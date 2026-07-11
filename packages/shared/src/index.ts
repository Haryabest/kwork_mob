/** Общие типы для всех клиентов */

export type UserRole = 'owner' | 'manager' | 'photographer' | 'viewer';

export type OrderStatus =
  | 'pending'
  | 'paid'
  | 'queued'
  | 'processing'
  | 'completed'
  | 'cancelled'
  | 'failed'
  | 'nsfw_blocked';

export type ProductCategory =
  | 'clothing'
  | 'shoes'
  | 'electronics'
  | 'furniture'
  | 'decor'
  | 'toys'
  | 'adult'
  | 'other';

export type Tier = 'small' | 'large';

export interface Order {
  id: number;
  task_uuid: string;
  category: ProductCategory;
  tier: Tier;
  status: OrderStatus;
  amount: number;
  created_at: string;
}

export interface Model3D {
  uuid: string;
  order_id: number;
  glb_url?: string;
  usdz_url?: string;
  publish_status: string;
  created_at: string;
}

export const PRICING = {
  small: 2990,
  large: 5990,
} as const;
