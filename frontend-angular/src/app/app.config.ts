import {
  ApplicationConfig,
  InjectionToken,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { providePrimeNG } from 'primeng/config';
import Aura from '@primeuix/themes/aura';

import { routes } from './app.routes';
import { provideClientHydration, withEventReplay } from '@angular/platform-browser';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { baseUrlInterceptor } from './interceptors/base-url-interceptor';
import { authInterceptor } from './interceptors/auth-interceptor';
import { MessageService } from 'primeng/api';
export const BASE_URL = new InjectionToken<string>('BASE_URL');
export const appConfig: ApplicationConfig = {
  providers: [
    { provide: BASE_URL, useValue: 'http://localhost:8000' },

    provideHttpClient(withFetch(), withInterceptors([baseUrlInterceptor, authInterceptor])),
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideClientHydration(withEventReplay()),
    providePrimeNG({
      theme: {
        preset: Aura,
      },
    }),
    MessageService,
  ],
};
