import { Badge, Button, Card, Group, Progress, SimpleGrid, Table, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

export function PageHeader({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <Group justify="space-between" align="flex-start" mb="lg"><div><Title order={2}>{title}</Title><Text c="dimmed" size="sm">{description}</Text></div>{action}</Group>;
}

export function MetricGrid({ items }: { items: { label: string; value: string; hint?: string; color?: string }[] }) {
  return <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} mb="lg">{items.map((item) => <Card key={item.label} withBorder><Text size="sm" c="dimmed">{item.label}</Text><Text fw={700} size="xl" mt={6}>{item.value}</Text>{item.hint && <Text size="xs" c={item.color ?? 'dimmed'} mt={4}>{item.hint}</Text>}</Card>)}</SimpleGrid>;
}

export function ShellTable({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return <Card withBorder padding={0} radius="md"><Table striped highlightOnHover horizontalSpacing="md" verticalSpacing="sm"><Table.Thead><Table.Tr>{headers.map((header) => <Table.Th key={header}>{header}</Table.Th>)}</Table.Tr></Table.Thead><Table.Tbody>{rows.map((row, index) => <Table.Tr key={index}>{row.map((cell, cellIndex) => <Table.Td key={cellIndex}>{cell}</Table.Td>)}</Table.Tr>)}</Table.Tbody></Table></Card>;
}

export function StateBadge({ value, color = 'blue' }: { value: string; color?: string }) {
  return <Badge color={color} variant="light">{value}</Badge>;
}

export function HealthCard({ name, status, load }: { name: string; status: string; load: number }) {
  return <Card withBorder><Group justify="space-between"><Text fw={600}>{name}</Text><StateBadge value={status} color={status === 'Онлайн' ? 'teal' : 'orange'} /></Group><Text size="sm" c="dimmed" mt="md">Загрузка: {load}%</Text><Progress value={load} color={load > 80 ? 'orange' : 'teal'} mt={6} /></Card>;
}

export const SaveButton = ({ children = 'Сохранить' }: { children?: ReactNode }) => <Button type="button">{children}</Button>;
