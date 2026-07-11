import { Card, Text, Title } from '@mantine/core';

export default function PageStub({ title, description }: { title: string; description: string }) {
  return (
    <>
      <Title order={2} mb="xs">
        {title}
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        {description}
      </Text>
      <Card withBorder padding="lg" radius="md">
        <Text size="sm">Раздел в разработке. API пока отвечает 501.</Text>
      </Card>
    </>
  );
}
