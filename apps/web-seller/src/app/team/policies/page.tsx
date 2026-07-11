'use client';

import { Button, Card, Checkbox, NumberInput, Select, Stack, Text, Title } from '@mantine/core';
import { SellerShell } from '../../../components/SellerShell';

export default function PoliciesPage() {
  return <SellerShell><Title order={2}>Политики доступа</Title><Text c="dimmed" size="sm" mb="lg">Ограничения по умолчанию для сотрудников</Text>
    <Card withBorder maw={620}><Stack><NumberInput label="Максимум одновременных заказов" min={1} max={20} defaultValue={3} /><NumberInput label="Лимит расходов в месяц, ₽" min={0} placeholder="Без ограничений" /><Select label="Доступные категории" data={['Все категории', 'Одежда', 'Обувь', 'Аксессуары']} defaultValue="Все категории" /><Checkbox label="Разрешить фотографам скачивание моделей" /><Checkbox label="Разрешить фотографам добавлять ссылки публикации" /><Button w="fit-content">Сохранить политики</Button></Stack></Card>
  </SellerShell>;
}
