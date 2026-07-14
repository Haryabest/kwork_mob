import { NextResponse } from 'next/server';

/**
 * iOS Universal Links AASA — TEAMID и bundle из env (§3.15).
 * Host = production SELLER_PUBLIC_URL / Next public URL.
 */
export function GET() {
  const team = (process.env.APPLE_TEAM_ID || process.env.NEXT_PUBLIC_APPLE_TEAM_ID || 'TEAMID').trim();
  const bundle = (
    process.env.IOS_BUNDLE_ID ||
    process.env.NEXT_PUBLIC_IOS_BUNDLE_ID ||
    'com.kwork.mob.kworkMobile'
  ).trim();

  const body = {
    applinks: {
      apps: [],
      details: [
        {
          appIDs: [`${team}.${bundle}`],
          components: [
            {
              '/': '/shoot/*',
              comment: '§3.15 shoot-link Universal Links',
            },
          ],
        },
      ],
    },
  };

  return NextResponse.json(body, {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=3600',
    },
  });
}
