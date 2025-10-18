// Custom global typings to satisfy TypeScript in this project

declare module 'recharts';
declare module 'lodash';

declare module 'sonner';

declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV?: 'development' | 'production' | 'test';
    NEXT_PUBLIC_API_URL?: string;
    NEXT_PUBLIC_AUTH_TOKEN?: string;
    // add other env vars here as needed
  }
}
