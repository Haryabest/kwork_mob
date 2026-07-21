'use client';

import { Button, Group, Text, Title } from '@mantine/core';
import Link from 'next/link';
import type { ReactNode } from 'react';

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="vz-page-header">
      <Group justify="space-between" align="flex-end" wrap="wrap" gap="md" w="100%">
        <div>
          <Title order={2} style={{ letterSpacing: '-0.03em' }}>
            {title}
          </Title>
          {description ? (
            <Text c="#6d6c77" size="sm" mt={6} maw={560}>
              {description}
            </Text>
          ) : null}
        </div>
        {action}
      </Group>
    </header>
  );
}

export function Surface({
  children,
  className = '',
  style,
  mb,
}: {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  mb?: string;
}) {
  const marginStyle = mb ? { marginBottom: `var(--mantine-spacing-${mb}, ${mb})` } : {};
  return (
    <section className={`vz-surface ${className}`.trim()} style={{ ...marginStyle, ...style }}>
      {children}
    </section>
  );
}

export function EmptyState({
  title,
  hint,
  actionLabel,
  actionHref,
}: {
  title: string;
  hint?: string;
  actionLabel?: string;
  actionHref?: string;
}) {
  return (
    <div className="vz-empty">
      <Text fw={600} size="lg">
        {title}
      </Text>
      {hint ? (
        <Text c="#6d6c77" size="sm" maw={420} ta="center" mt={8}>
          {hint}
        </Text>
      ) : null}
      {actionLabel && actionHref ? (
        <Button component={Link} href={actionHref} mt="lg">
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}

export function SubNav({ items }: { items: { href: string; label: string }[] }) {
  return (
    <div className="vz-subnav">
      {items.map((item) => (
        <Button key={item.href} component={Link} href={item.href} variant="light" size="sm" radius="xl">
          {item.label}
        </Button>
      ))}
    </div>
  );
}

export function FilterRow({ children, mb }: { children: ReactNode; mb?: string }) {
  const marginStyle = mb ? { marginBottom: `var(--mantine-spacing-${mb}, ${mb})` } : undefined;
  return (
    <div className="vz-filters" style={marginStyle}>
      {children}
    </div>
  );
}

export function ScrollTable({ children }: { children: ReactNode }) {
  return <div className="vz-table-scroll">{children}</div>;
}
