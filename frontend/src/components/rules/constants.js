/**
 * Constants for rule management.
 */

// Fallback suggested apps (shown when no usage data available)
export const DEFAULT_SUGGESTED_APPS = [
  { name: 'Epic Games', keyword: 'Epic' },
  { name: 'Steam', keyword: 'Steam' },
  { name: 'Discord', keyword: 'Discord' },
  { name: 'Chrome', keyword: 'Chrome' },
  { name: 'Roblox', keyword: 'Roblox' },
  { name: 'Minecraft', keyword: 'Minecraft' }
]

// Initial form state for new rules
export const INITIAL_FORM_DATA = {
  rule_type: 'app_block',
  name: '',
  app_name: '',
  website_url: '',
  time_limit: '',
  enabled: true,
  schedule_start_time: '',
  schedule_end_time: '',
  schedule_days: '',
  block_network: false
}

// Apps to filter out from suggestions (system services)
export const SYSTEM_APP_PATTERNS = [
  'service', 'host', 'helper', 'system', 'windows', 'svchost'
]
