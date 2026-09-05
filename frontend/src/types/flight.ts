export interface Airport {
  code: string;
  name: string;
  city: string;
  country: string;
  latitude?: number;
  longitude?: number;
  hub_score?: number;
}

export interface DealInfo {
  score: 'GREAT_DEAL' | 'GOOD_DEAL' | 'REGULAR_PRICE';
  tier: 'green' | 'yellow' | 'red';
  badge: string;
  is_great_deal: boolean;
  discount_pct: number;
  message: string;
}

export interface FlightLeg {
  origin: string;
  destination: string;
  airline: string;
  flight_number: string;
  price: number;
  departure_date: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  platform_prices?: Record<string, number>;
  cheapest_platform?: string;
}

export interface DirectOption {
  is_direct: boolean;
  has_direct_flight?: boolean;
  airline: string;
  flight_number: string;
  price: number;
  avg_60d: number;
  avg_30d: number;
  deal_info: DealInfo;
  legs: FlightLeg[];
}

export interface SplitOption {
  hub: Airport;
  total_price: number;
  avg_60d: number;
  avg_30d: number;
  deal_info: DealInfo;
  savings_vs_direct: number;
  savings_pct_vs_direct: number;
  is_best_split: boolean;
  detour_ratio: number;
  layover_duration: string;
  total_duration: string;
  leg1: FlightLeg;
  leg2: FlightLeg;
}

export interface DateCandidate {
  departure_date: string;
  return_date?: string;
  direct_price: number;
  best_split_price: number;
  best_hub: string;
  savings: number;
  is_cheapest_in_range: boolean;
}

export interface RangeAnalysis {
  range_start: string;
  range_end: string;
  trip_duration_days: number;
  cheapest_departure_date: string;
  cheapest_return_date: string;
  cheapest_package_price: number;
  cheapest_hub: string;
  max_range_savings: number;
  date_candidates: DateCandidate[];
}

export interface ScraperStatus {
  is_live: boolean;
  source: string;
  status_badge: string;
  message: string;
}

export interface SearchResponse {
  origin: Airport;
  destination: Airport;
  target_month: string;
  trip_type: 'round_trip' | 'one_way';
  outbound_date: string;
  return_date?: string;
  direct_option: DirectOption;
  split_options: SplitOption[];
  return_direct_option?: DirectOption;
  return_split_options?: SplitOption[];
  total_round_trip_direct_price?: number;
  total_round_trip_best_split_price?: number;
  round_trip_savings?: number;
  combined_60d_avg_direct?: number;
  combined_60d_avg_split?: number;
  combined_deal_info?: DealInfo;
  range_analysis?: RangeAnalysis;
  scraper_status?: ScraperStatus;
  search_timestamp: string;
}

export interface GreatDealItem {
  origin: string;
  destination: string;
  current_price: number;
  avg_60d: number;
  avg_30d: number;
  deal_info: DealInfo;
}

export interface TrackedLegDetail {
  origin: string;
  destination: string;
  airline: string;
  flight_number: string;
  departure_date?: string;
  departure_time: string;
  arrival_time: string;
  duration: string;
  price: number;
  platform_prices?: Record<string, number>;
  cheapest_platform?: string;
  layover_after?: {
    airport: string;
    duration: string;
  } | null;
}

export interface TrackedRouteItem {
  id: number;
  origin: Airport;
  destination: Airport;
  range_start: string;
  range_end: string;
  trip_duration_days: number;
  trip_type: string;
  has_direct_flight: boolean;
  best_hub: string;
  estimated_price: number;
  avg_60d: number;
  deal_info: DealInfo;
  outbound_legs?: TrackedLegDetail[];
  return_legs?: TrackedLegDetail[];
  leg1?: TrackedLegDetail | null;
  leg2?: TrackedLegDetail | null;
  return_leg1?: TrackedLegDetail | null;
  return_leg2?: TrackedLegDetail | null;
  status?: string;
  status_message?: string;
  is_active: boolean;
  created_at: string;
}
