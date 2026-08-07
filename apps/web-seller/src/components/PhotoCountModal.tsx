'use client';

import { Button, Modal, SimpleGrid, Stack, Text } from '@mantine/core';
import { useRouter } from 'next/navigation';

const MODES = [
  { count: 1, title: '1 фото', hint: 'Быстрое оформление по одному снимку' },
  { count: 3, title: '3 фото', hint: 'Фронт + лево 90° + тыл' },
  { count: 5, title: '5 фото', hint: 'Равномерно по кругу каждые 60°' },
  { count: 6, title: '6 фото', hint: 'Шесть ракурсов каждые 60°' },
] as const;

type Props = {
  opened: boolean;
  onClose: () => void;
};

export function PhotoCountModal({ opened, onClose }: Props) {
  const router = useRouter();

  function go(count: number) {
    onClose();
    router.push(`/orders/new?photo_count=${count}`);
  }

  return (
    <Modal opened={opened} onClose={onClose} title="Сколько фото?" centered radius="lg">
      <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="sm">
        {MODES.map((m) => (
          <Button key={m.count} variant="light" h="auto" py="md" onClick={() => go(m.count)}>
            <Stack gap={4} align="center">
              <Text fw={600}>{m.title}</Text>
              <Text size="xs" c="dimmed" ta="center">
                {m.hint}
              </Text>
            </Stack>
          </Button>
        ))}
      </SimpleGrid>
    </Modal>
  );
}

export const PHOTO_COUNT_MODES = MODES;
