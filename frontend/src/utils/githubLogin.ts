/** GitHub login 比较（忽略大小写与首尾空格）。 */
export function githubLoginEquals(a: string, b: string): boolean {
  return a.trim().toLowerCase() === b.trim().toLowerCase()
}
