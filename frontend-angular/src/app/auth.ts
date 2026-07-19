import { HttpClient, HttpParams, HttpResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom, map, Observable, tap } from 'rxjs';

interface TokenResponse {
  access_token: string;
  token_type: string;
}

@Injectable({
  providedIn: 'root',
})
export class Auth {
  private http = inject(HttpClient);
  private TOKEN_KEY = 'access_token';

  constructor() {}
  public async login(userName: string, password: string) {
    const body = new HttpParams().set('username', userName).set('password', password);
    try {
      const response = await firstValueFrom(
        this.http.post<TokenResponse>('/auth/login', body.toString(), {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }),
      );

      this.setAccessToken(response.access_token);
      return response;
    } catch (error) {
      console.error('Login failed', error);
      throw error;
    }
  }

  public logout() {
    this.removeAccessToken();
    this.http.get('/auth/logout');
  }
  public refreshToken(): Observable<{ accessToken: string }> {
    return this.http
      .post<{ accessToken: string }>('/auth/refresh-token', {}, { withCredentials: true })
      .pipe(tap(({ accessToken }) => this.setAccessToken(accessToken)));
  }
  // Store token securely
  private setAccessToken(token: string): void {
    sessionStorage.setItem(this.TOKEN_KEY, token);
  }
  // Retrieve token
  public getAccessToken(): string | null {
    return sessionStorage.getItem(this.TOKEN_KEY);
  }
  // Remove token
  private removeAccessToken(): void {
    sessionStorage.removeItem(this.TOKEN_KEY);
  }
}
