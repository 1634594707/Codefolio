import React from 'react'
import {
  Code2,
  Database,
  Cloud,
  GitBranch,
  Zap,
  Package,
  Layers,
  Terminal,
  Cpu,
  Smartphone,
  Palette,
  Boxes,
  Workflow,
  Shield,
  Gauge,
  Hexagon,
  type LucideIcon,
} from 'lucide-react'

// Map programming languages to Lucide icons
// Using a generic icon set that works well for most languages
const LANGUAGE_ICON_MAP: Record<string, LucideIcon> = {
  // Languages
  python: Code2,
  javascript: Code2,
  typescript: Code2,
  java: Code2,
  csharp: Code2,
  'c#': Code2,
  cpp: Code2,
  'c++': Code2,
  c: Cpu,
  assembly: Cpu,
  asm: Cpu,
  go: Code2,
  rust: Code2,
  php: Code2,
  ruby: Code2,
  kotlin: Code2,
  swift: Code2,
  scala: Code2,
  haskell: Code2,
  elm: Code2,
  clojure: Code2,
  perl: Code2,
  lua: Code2,
  r: Code2,
  matlab: Code2,
  julia: Code2,
  dart: Code2,

  // Frontend Frameworks
  react: Layers,
  vue: Layers,
  angular: Layers,
  svelte: Layers,
  nextjs: Layers,
  'next.js': Layers,
  flutter: Smartphone,
  'react native': Smartphone,
  xamarin: Smartphone,

  // Backend Frameworks
  node: Terminal,
  nodejs: Terminal,
  'node.js': Terminal,
  django: Terminal,
  fastapi: Terminal,
  flask: Terminal,
  springboot: Terminal,
  'spring boot': Terminal,

  // Databases
  postgresql: Database,
  postgres: Database,
  mongodb: Database,
  mysql: Database,
  redis: Database,
  elasticsearch: Database,

  // DevOps & Cloud
  docker: Package,
  kubernetes: Package,
  aws: Cloud,
  gcp: Cloud,
  'google cloud': Cloud,
  azure: Cloud,
  git: GitBranch,
  linux: Terminal,
  shell: Terminal,
  bash: Terminal,
  zsh: Terminal,
  powershell: Terminal,

  // Message Queues
  rabbitmq: Workflow,
  kafka: Workflow,

  // APIs & Protocols
  graphql: Hexagon,

  // Build Tools
  webpack: Boxes,
  vite: Zap,
  rollup: Boxes,
  parcel: Boxes,
  gulp: Workflow,
  grunt: Workflow,

  // Transpilers & Linters
  babel: Zap,
  eslint: Shield,
  prettier: Palette,

  // Testing
  jest: Gauge,
  mocha: Gauge,
  jasmine: Gauge,
  cypress: Gauge,
  selenium: Gauge,
  playwright: Gauge,

  // Game Engines
  unity: Cpu,
  unreal: Cpu,
  godot: Cpu,

  // Design Tools
  figma: Palette,
  sketch: Palette,
  framer: Palette,

  // Version Control
  github: GitBranch,
  gitlab: GitBranch,
  bitbucket: GitBranch,

  // Collaboration
  jira: Workflow,
  confluence: Workflow,
  notion: Workflow,
  slack: Terminal,
  discord: Terminal,
}

interface TechStackIconProps {
  language: string
  size?: number
  className?: string
}

export const TechStackIcon: React.FC<TechStackIconProps> = ({ language, size = 24, className = '' }) => {
  const normalizedLanguage = language.toLowerCase().trim()
  const IconComponent = LANGUAGE_ICON_MAP[normalizedLanguage]

  if (!IconComponent) {
    return null
  }

  return <IconComponent size={size} className={className} />
}

export const getTechStackIcon = (language: string) => {
  const normalizedLanguage = language.toLowerCase().trim()
  return LANGUAGE_ICON_MAP[normalizedLanguage]
}

export default LANGUAGE_ICON_MAP
