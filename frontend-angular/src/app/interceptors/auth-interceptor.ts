import {
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
  HttpErrorResponse,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { Auth } from '../auth';

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
) => {
  const authService = inject(Auth);

  const addToken = (request: HttpRequest<unknown>) =>
    authService.getAccessToken()
      ? request.clone({
          setHeaders: { Authorization: `Bearer ${authService.getAccessToken()}` },
        })
      : request;

  return next(addToken(req)).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status == 401) {
        return authService.refreshToken().pipe(
          switchMap(() => next(addToken(req))),
          catchError((refreshError) => throwError(() => refreshError)),
        );
      }

      return throwError(() => error);
    }),
  );
};
