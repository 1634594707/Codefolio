export function formatContributionTooltip(
  language: 'en' | 'zh',
  date: string,
  count: number,
): string {
  const contributionLabel = language === 'zh' ? '次贡献' : 'contributions'
  return `${date}: ${count} ${contributionLabel}`
}
