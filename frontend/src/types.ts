export interface LocationDTO {
  id: number
  code: string
  name: string
  address: string
  lane_count: number
  active_order_count: number
}

export interface LaneDTO {
  id: number
  location_id: number
  slot_no: string
  sku_name: string
  capacity: number
  stock: number
  in_transit: number
  gap: number
  fill_pct: number
}

export interface SaleDTO {
  id: number
  location_id: number
  lane_id: number
  slot_no: string
  sku_name: string
  qty: number
  sold_at: string
}

export interface RefillLineDTO {
  lane_id: number | null
  slot_no: string
  sku_name: string
  capacity: number
  stock: number
  in_transit: number
  gap: number
  fill_qty: number
  status: 'need_fill' | 'full' | 'overbooked'
}

export interface RefillOrderDTO {
  id: number
  location_id: number
  created_at: string
  status: 'active' | 'void'
  voided_at: string | null
  total_fill: number
  need_fill_count: number
  full_count: number
  overbooked_count: number
  lines: RefillLineDTO[]
}
