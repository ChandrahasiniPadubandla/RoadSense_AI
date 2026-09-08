import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3 bg-asphalt-950 text-center">
      <p className="text-lg text-asphalt-100">Page not found</p>
      <p className="text-sm text-asphalt-400">
        The page you're looking for doesn't exist.
      </p>
      <Link to="/" className="text-sm text-signal-blue hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}
