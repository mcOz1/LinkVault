import difflib
import os
from pathlib import Path
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from fastapi import Depends, HTTPException, UploadFile, status
import httpx
from sqlmodel import select

from links.models import Link, Tag2Link, Tag
from authentication.models import User
from authentication.services import auth_service
from server import session, settings


class LinkService:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
        "Referer": "https://www.google.com/"
    }
    def __init__(
        self,
        session: session.SessionDep,
        user: User = Depends(auth_service.get_current_active_user)
        ):
        self._session = session
        self._user = user
    
    async def create_link(self, url: str):
        if not self._user or not self._user.id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")
        try:
            # We use httpx asynchronously, which is ideal for FastAPI
            async with httpx.AsyncClient(timeout=10.0, headers=self.HEADERS, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            image = soup.find('meta', property="og:image")
            image_path = await self.fetch_and_save_og_image(image, url)
            title = soup.find("meta", property="og:title")
            link = Link(
                url=url,
                created_by_id=self._user.id,
                title=title.get_text() if title else "",
                )
            if image_path:
                link.image = image_path
            self._session.add(link)
            await self._session.commit()
            await self._session.refresh(link)
            tags = await self.process_link_keywords(link=link, soup=soup)
            return link
        except Exception as e:
            print(e)
            await self._session.rollback()
            raise
    
    async def fetch_keywords_from_url(self, soup: BeautifulSoup) -> list[str]:
        """Fetches the webpage and extracts the content of the 'keywords' meta tag."""
        try:
            
            # Search for the <meta name="keywords" ...> tag (case-insensitive)
            meta_keywords = soup.find('meta', {'name': 'keywords'})
            
            if meta_keywords and meta_keywords.get('content'):
                # Split by comma, remove whitespace, and convert to lowercase
                raw_keywords = meta_keywords['content']
                raw_keywords_str = str(raw_keywords)
                raw_keywords_list = raw_keywords_str.split(',')
                return [kw.strip().lower() for kw in raw_keywords_list if kw.strip()]
                
            return []
        except Exception as e:
            print(e)
            return []
    async def get_or_create_tag(self, raw_keyword: str) -> Tag | None:
        """
        Finds an exact match, a fuzzy (similar) match, or creates a new tag.
        """
        normalized_kw = self.normalize_tag_string(raw_keyword)
        
        if not normalized_kw:
            return None

        # 1. Check for an exact match in the database
        exact_match_stmt = select(Tag).where(Tag.name == normalized_kw)
        exact_tag = await self._session.scalar(exact_match_stmt)
        
        if exact_tag:
            return exact_tag

        # 2. Fuzzy Matching to catch typos or similar tags (e.g. "fastapi" vs "fast-api")
        # Note: Fetching all tags is fine for small/medium DBs. 
        # For massive DBs, you'd use database-level similarity functions (like pg_trgm in PostgreSQL).
        all_tags_stmt = select(Tag.name)
        existing_tag_names = (await self._session.scalars(all_tags_stmt)).all()
        
        # Find tags that are at least 85% similar (cutoff=0.85)
        similar_matches = difflib.get_close_matches(
            normalized_kw, existing_tag_names, n=1, cutoff=0.85
        )
        
        if similar_matches:
            similar_tag_name = similar_matches[0]
            # Fetch the matched tag from DB
            similar_match_stmt = select(Tag).where(Tag.name == similar_tag_name)
            return await self._session.scalar(similar_match_stmt)

        # 3. If no exact or similar match is found, create a new tag
        new_tag = Tag(name=normalized_kw)
        self._session.add(new_tag)
        await self._session.commit()
        await self._session.refresh(new_tag)
        
        return new_tag

    async def assign_tags_to_link(self, link: Link, keywords: list[str]):
        if not link or not link.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

        for raw_kw in set(keywords):
            tag = await self.get_or_create_tag(raw_kw)
            
            if not tag or not tag.id:
                continue

            stmt = select(Tag2Link).where(
            Tag2Link.link_id == link.id,
            Tag2Link.tag_id == tag.id
            )
            
            result = await self._session.execute(stmt)
            existing_relation = result.first()

            if not existing_relation:
                new_relation = Tag2Link(link_id=link.id, tag_id=tag.id)
                self._session.add(new_relation)
        await self._session.commit()

    async def process_link_keywords(self, link: Link, soup: BeautifulSoup):
        keywords = await self.fetch_keywords_from_url(soup)
        if keywords:
            await self.assign_tags_to_link(link, keywords)
    
    def normalize_tag_string(self, raw_tag: str) -> str:
        """
        Normalizes the tag string to prevent basic duplicates.
        Example: " Vue.js! " -> "vue-js", "Machine   Learning" -> "machine-learning"
        """
        # 1. Lowercase and strip outer whitespace
        tag = raw_tag.lower().strip()
        
        # 2. Replace common separators (dots, underscores) with spaces
        tag = re.sub(r'[\._]', ' ', tag)
        
        # 3. Remove all characters except alphanumerics, spaces, and hyphens
        tag = re.sub(r'[^\w\s-]', '', tag)
        
        # 4. Collapse multiple spaces or hyphens into a single hyphen (slug format)
        tag = re.sub(r'[-\s]+', '-', tag)
        
        return tag.strip('-')
    
    async def fetch_and_save_og_image(self, og_image_meta, page_url: str):
        
        if not og_image_meta or not og_image_meta.get('content'):
            print(f"No og:image found on {page_url}")
            return None
            
        raw_image_url = og_image_meta['content']
        
        # 3. Ensure the URL is absolute (sometimes they are relative like "/images/cover.jpg")
        absolute_image_url = urljoin(page_url, raw_image_url)
        
        async with httpx.AsyncClient(timeout=10.0, headers=self.HEADERS, follow_redirects=True) as client:
        # 4. Fetch the actual image data
            image_response = await client.get(absolute_image_url)
            image_response.raise_for_status()
        
        # 5. Determine a file name
        # A simple way to get the file name from the URL, ignoring URL parameters like ?v=123
        filename = absolute_image_url.split('/')[-1].split('?')[0]
        
        # Fallback if the URL doesn't end with a clean file name
        if not filename:
            filename = "default_cover.jpg"
            
        save_directory = Path(settings.BASE_UPLOAD_DIR) / "link_avatars"
        save_directory.mkdir(parents=True, exist_ok=True)
        image_path = save_directory / filename
        image_path.write_bytes(image_response.content)
            
        print(f"Successfully saved image to: {image_path}")
        return str(image_path)
    