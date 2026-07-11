'use client';

import { Button, Card, Checkbox, NumberInput, PasswordInput, Select, Stack, Tabs, Text, TextInput, Title } from '@mantine/core';
import { SellerShell } from '../../components/SellerShell';

export default function SettingsPage() {
  return (
    <SellerShell>
      <Title order={2} mb="xs">
        Настройки
      </Title>
      <Text c="dimmed" size="sm" mb="lg">
        Профиль, безопасность, уведомления
      </Text>
      <Tabs defaultValue="profile"><Tabs.List><Tabs.Tab value="profile">Профиль</Tabs.Tab><Tabs.Tab value="security">Безопасность</Tabs.Tab><Tabs.Tab value="notifications">Уведомления</Tabs.Tab><Tabs.Tab value="appearance">Внешний вид</Tabs.Tab><Tabs.Tab value="company">Компания</Tabs.Tab><Tabs.Tab value="danger" color="red">Опасная зона</Tabs.Tab></Tabs.List>
        <Tabs.Panel value="profile" pt="lg"><Card withBorder maw={600}><Stack><TextInput label="Имя" /><TextInput label="Email" type="email" /><TextInput label="Телефон" /><Button w="fit-content">Сохранить профиль</Button></Stack></Card></Tabs.Panel>
        <Tabs.Panel value="security" pt="lg"><Card withBorder maw={600}><Stack><PasswordInput label="Текущий пароль" /><PasswordInput label="Новый пароль" /><Checkbox label="Включить двухфакторную аутентификацию" /><Button w="fit-content">Обновить безопасность</Button></Stack></Card></Tabs.Panel>
        <Tabs.Panel value="notifications" pt="lg"><Card withBorder maw={600}><Stack><Checkbox label="Email-уведомления о заказах" defaultChecked /><Checkbox label="Email-уведомления о балансе" defaultChecked /><Checkbox label="Уведомления о готовых моделях" defaultChecked /><Button w="fit-content">Сохранить</Button></Stack></Card></Tabs.Panel>
        <Tabs.Panel value="appearance" pt="lg"><Card withBorder maw={600}><Stack><Select label="Тема" data={['Системная', 'Светлая', 'Тёмная']} defaultValue="Системная" /><Select label="Язык" data={['Русский']} defaultValue="Русский" /><Button w="fit-content">Сохранить</Button></Stack></Card></Tabs.Panel>
        <Tabs.Panel value="company" pt="lg"><Card withBorder maw={600}><Stack><TextInput label="Название компании" /><NumberInput label="Порог низкого баланса, ₽" placeholder="5000" /><Button w="fit-content">Сохранить компанию</Button></Stack></Card></Tabs.Panel>
        <Tabs.Panel value="danger" pt="lg"><Card withBorder maw={600}><Stack><Text fw={600} c="red">Удаление аккаунта</Text><Text size="sm" c="dimmed">Все данные будут удалены без возможности восстановления.</Text><Button color="red" variant="light" w="fit-content">Удалить аккаунт</Button></Stack></Card></Tabs.Panel>
      </Tabs>
    </SellerShell>
  );
}
