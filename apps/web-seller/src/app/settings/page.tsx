'use client';

import {
  Button,
  Checkbox,
  NumberInput,
  PasswordInput,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
} from '@mantine/core';
import { SellerShell } from '../../components/SellerShell';
import { PageHeader, Surface } from '../../components/ui';

/** §20.8 Профиль и настройки */
export default function SettingsPage() {
  return (
    <SellerShell>
      <PageHeader title="Профиль и настройки" description="Личные данные, безопасность, компания и уведомления" />

      <Tabs defaultValue="profile">
        <Tabs.List mb="lg">
          <Tabs.Tab value="profile">Профиль</Tabs.Tab>
          <Tabs.Tab value="security">Безопасность</Tabs.Tab>
          <Tabs.Tab value="notifications">Уведомления</Tabs.Tab>
          <Tabs.Tab value="appearance">Внешний вид</Tabs.Tab>
          <Tabs.Tab value="company">Компания</Tabs.Tab>
          <Tabs.Tab value="danger" color="red">
            Опасная зона
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="profile">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <TextInput label="Имя" size="md" />
              <TextInput label="Email" type="email" size="md" />
              <TextInput label="Телефон" size="md" />
              <Button w={{ base: '100%', sm: 'fit-content' }}>Сохранить профиль</Button>
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="security">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <PasswordInput label="Текущий пароль" size="md" />
              <PasswordInput label="Новый пароль" size="md" />
              <Checkbox label="Включить двухфакторную аутентификацию (Owner)" />
              <Button w={{ base: '100%', sm: 'fit-content' }}>Обновить безопасность</Button>
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="notifications">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Checkbox label="Email о заказах" defaultChecked />
              <Checkbox label="Email о балансе" defaultChecked />
              <Checkbox label="Уведомления о готовых моделях" defaultChecked />
              <Button w={{ base: '100%', sm: 'fit-content' }}>Сохранить</Button>
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="appearance">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Select label="Тема" data={['Системная', 'Светлая', 'Тёмная']} defaultValue="Светлая" size="md" />
              <Select label="Язык" data={['Русский']} defaultValue="Русский" size="md" />
              <Button w={{ base: '100%', sm: 'fit-content' }}>Сохранить</Button>
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="company">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Text size="sm" c="#6d6c77">
                Для юридических лиц (Owner): реквизиты и порог низкого баланса
              </Text>
              <TextInput label="Название компании" size="md" />
              <NumberInput label="Порог низкого баланса, ₽" placeholder="5000" size="md" />
              <Button w={{ base: '100%', sm: 'fit-content' }}>Сохранить компанию</Button>
            </Stack>
          </Surface>
        </Tabs.Panel>

        <Tabs.Panel value="danger">
          <Surface style={{ maxWidth: 560 }}>
            <Stack gap="md">
              <Text fw={700} c="red">
                Удаление аккаунта
              </Text>
              <Text size="sm" c="#6d6c77">
                Все данные (модели, фото, персональные данные) будут удалены без восстановления.
              </Text>
              <Button color="red" variant="light" w={{ base: '100%', sm: 'fit-content' }}>
                Удалить аккаунт
              </Button>
            </Stack>
          </Surface>
        </Tabs.Panel>
      </Tabs>
    </SellerShell>
  );
}
