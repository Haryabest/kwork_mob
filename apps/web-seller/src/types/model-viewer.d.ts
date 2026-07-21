import type React from 'react';

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string;
        'camera-controls'?: string | boolean;
        'auto-rotate'?: string | boolean;
        'touch-action'?: string;
        exposure?: string;
        'shadow-intensity'?: string;
        'camera-orbit'?: string;
        'min-camera-orbit'?: string;
        'max-camera-orbit'?: string;
      };
    }
  }
}
