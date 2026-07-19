import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { BASE_URL } from '../app.config';

export const baseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  // Inject the base URL token
  const baseUrl = inject(BASE_URL);

  // Ignore requests that already have an absolute URL to avoid malformed addresses
  if (req.url.startsWith('http')) {
    return next(req);
  }

  // Clone the request and prepend the base URL
  const apiReq = req.clone({
    url: `${baseUrl}${req.url}`,
  });

  // Pass the modified request to the next handler
  return next(apiReq);
};
