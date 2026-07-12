import { Badge, Button, Group, Progress, Table, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="vz-page-header">
      <div>
        <Title order={2}>{title}</Title>
        <Text c="#6d6c77" size="sm" mt={6}>
          {description}
        </Text>
      </div>
      {action}
    </div>
  );
}

export function MetricGrid({
  items,
}: {
  items: { label: string; value: string; hint?: string; color?: string }[];
}) {
  return (
    <div className="vz-grid vz-grid-2 vz-grid-4">
      {items.map((item) => (
        <div key={item.label} className="vz-surface">
          <Text size="sm" c="#6d6c77">
            {item.label}
          </Text>
          <Text fw={700} size="xl" mt={10} className="vz-metric-value">
            {item.value}
          </Text>
          {item.hint && (
            <Text size="xs" c={item.color ?? 'dimmed'} mt={8}>
              {item.hint}
            </Text>
          )}
        </div>
      ))}
    </div>
  );
}

export function ShellTable({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return (
    <div className="vz-surface" style={{ padding: 0 }}>
      <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
        <Table striped highlightOnHover horizontalSpacing="md" verticalSpacing="md" miw={560}>
          <Table.Thead>
            <Table.Tr>
              {headers.map((header) => (
                <Table.Th key={header}>{header}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((row, index) => (
              <Table.Tr key={index}>
                {row.map((cell, cellIndex) => (
                  <Table.Td key={cellIndex}>{cell}</Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>
    </div>
  );
}

export function StateBadge({ value, color = 'brand' }: { value: string; color?: string }) {
  return (
    <Badge color={color} variant="light" radius="sm">
      {value}
    </Badge>
  );
}

export function HealthCard({ name, status, load }: { name: string; status: string; load: number }) {
  return (
    <div className="vz-surface">
      <Group justify="space-between">
        <Text fw={600}>{name}</Text>
        <StateBadge value={status} color={status === 'Онлайн' ? 'teal' : 'orange'} />
      </Group>
      <Text size="sm" c="#6d6c77" mt="lg">
        Загрузка: {load}%
      </Text>
      <Progress
        value={load}
        color={load > 80 ? 'orange' : 'brand'}
        mt="sm"
        size="md"
        radius="xl"
      />
    </div>
  );
}

export const SaveButton = ({ children = 'Сохранить' }: { children?: ReactNode }) => (
  <Button type="button">{children}</Button>
);
