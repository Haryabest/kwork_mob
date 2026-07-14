import { NextResponse } from 'next/server';

/** Android App Links — package + SHA256 fingerprints из env (§3.15). */
export function GET() {
  const pkg = (
    process.env.ANDROID_PACKAGE_NAME ||
    process.env.NEXT_PUBLIC_ANDROID_PACKAGE_NAME ||
    'com.kwork.mob.kwork_mobile'
  ).trim();
  const raw =
    process.env.ANDROID_SHA256_FINGERPRINTS ||
    process.env.NEXT_PUBLIC_ANDROID_SHA256_FINGERPRINTS ||
    '';
  const fingerprints = raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

  const body = [
    {
      relation: ['delegate_permission/common.handle_all_urls'],
      target: {
        namespace: 'android_app',
        package_name: pkg,
        sha256_cert_fingerprints: fingerprints,
      },
    },
  ];

  return NextResponse.json(body, {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=3600',
    },
  });
}
