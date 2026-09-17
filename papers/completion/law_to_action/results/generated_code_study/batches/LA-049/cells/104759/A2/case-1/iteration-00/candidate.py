import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable()
export class AngularServerSideConfigurationService {
  private readonly configUrl = 'assets/config.json';

  constructor(private http: HttpClient) {}

  getConfig(): Observable<any> {
    return this.http.get<any>(this.configUrl)
      .pipe(
        map(config => {
          // Extract environment variables used in TypeScript files
          const usedEnvVars = config.environmentVariables || [];
          
          // Emit the configuration through the allowed handler
          emit_allowed({
            environmentVariables: usedEnvVars,
            source: 'angular-server-side-configuration',
            kind: 'build-time-configuration'
          });
        })
      );
  }
}