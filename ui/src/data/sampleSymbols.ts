export interface SymbolRecord {
  id: string;
  name: string;
  domain: string;
  tags: string[];
  summary: string;
  metadata: Record<string, string | number | boolean>;
  linkedSymbolIds: string[];
}

export const sampleSymbols: SymbolRecord[] = [
  {
    id: 'agent/core/planner',
    name: 'Planner Agent',
    domain: 'agents',
    tags: ['planner', 'workflow'],
    summary:
      'Orchestrates symbol relationships to break down complex goals into actionable steps.',
    metadata: {
      version: '1.3.0',
      owner: 'core-team',
      lastUpdated: '2024-01-12'
    },
    linkedSymbolIds: ['agent/core/memory', 'agent/plugins/retriever']
  },
  {
    id: 'agent/core/memory',
    name: 'Memory Manager',
    domain: 'agents',
    tags: ['memory', 'store'],
    summary: 'Persists contextual state across reasoning cycles and handles TTL enforcement.',
    metadata: {
      version: '2.0.0',
      owner: 'data-team',
      capacity: '512 entries'
    },
    linkedSymbolIds: ['agent/core/planner']
  },
  {
    id: 'agent/plugins/retriever',
    name: 'Context Retriever',
    domain: 'plugins',
    tags: ['retrieval', 'memory', 'redis'],
    summary: 'Locates relevant context from Redis using hybrid vector and keyword search.',
    metadata: {
      version: '0.9.5',
      owner: 'plugins-team',
      latencyMs: 42
    },
    linkedSymbolIds: ['agent/core/memory']
  },
  {
    id: 'domain/security/rbac',
    name: 'Role Based Access Policy',
    domain: 'security',
    tags: ['policy', 'security'],
    summary:
      'Defines the hierarchical role model for symbol access within Signal Zero deployments.',
    metadata: {
      version: '1.0.1',
      owner: 'security-team',
      enforced: true
    },
    linkedSymbolIds: []
  }
];
