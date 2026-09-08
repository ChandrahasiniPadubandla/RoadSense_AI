import React from 'react';
import { Link } from 'react-router-dom';

export default function Unauthorized() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3 bg-asphalt-950 text-center">
      <p className="text-lg text-asphalt-100">Access restricted</p>
      <p className="text-sm text-asphalt-400">
        Your role doesn't have permission to view this page.
      </p>
      <Link to="/" className="text-sm text-signal-blue hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}
