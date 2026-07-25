import { useState, useEffect } from 'react'

type Tab = 'chat' | 'agents' | 'history' | 'monitoring'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat')

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'chat', label: 'Chat', icon: '💬' },
    { id: 'agents', label: 'Agentes', icon: '🤖' },
    { id: 'history', label: 'Histórico', icon: '📋' },
    { id: 'monitoring', label: 'Monitoramento', icon: '📊' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🧠</span>
            <h1 className="text-lg font-semibold text-white">IA-Lab Enterprise</h1>
            <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">v0.1</span>
          </div>
          <nav className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                }`}
              >
                <span>{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {activeTab === 'chat' && <ChatTab />}
        {activeTab === 'agents' && <AgentsTab />}
        {activeTab === 'history' && <HistoryTab />}
        {activeTab === 'monitoring' && <MonitoringTab />}
      </main>
    </div>
  )
}

// ---- Chat Tab ----

function ChatTab() {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedAgent, setSelectedAgent] = useState('')
  const [providers, setProviders] = useState<{ name: string; configured: boolean }[]>([])
  const [agents, setAgents] = useState<{ name: string; task_type: string }[]>([])

  // Load providers and agents on mount
  useEffect(() => {
    fetch('/api/providers').then(r => r.json()).then(d => setProviders(d.providers)).catch(() => {})
    fetch('/api/agents').then(r => r.json()).then(d => setAgents(d.agents)).catch(() => {})
  }, [])

  const handleSubmit = async () => {
    if (!prompt.trim() || loading) return
    setLoading(true)
    setResponse('')

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          provider: selectedProvider || null,
          agent: selectedAgent || null,
          use_rag: true,
        }),
      })
      const data = await res.json()
      setResponse(data.response || JSON.stringify(data))
    } catch (err) {
      setResponse(`Erro: ${err}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Controls */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select
          name="agent"
          value={selectedAgent}
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
        >
          <option value="">Agente automático</option>
          {agents.map((a) => (
            <option key={a.name} value={a.name}>{a.name} ({a.task_type})</option>
          ))}
        </select>
        <select
          name="provider"
          value={selectedProvider}
          onChange={(e) => setSelectedProvider(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
        >
          <option value="">Provider automático</option>
          {providers.map((p) => (
            <option key={p.name} value={p.name} disabled={!p.configured}>
              {p.name} {p.configured ? '' : '(sem chave)'}
            </option>
          ))}
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {prompt && !loading && (
          <div className="flex justify-end">
            <div className="bg-indigo-600/20 border border-indigo-500/20 rounded-2xl rounded-br-md px-4 py-3 max-w-[80%]">
              <p className="text-sm text-gray-200">{prompt}</p>
            </div>
          </div>
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        {response && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-md px-4 py-3 max-w-[80%]">
              <p className="text-sm text-gray-200 whitespace-pre-wrap">{response}</p>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          name="prompt"
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
          placeholder="Digite sua mensagem..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
          disabled={loading}
        />
        <button
          onClick={handleSubmit}
          disabled={loading || !prompt.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-5 py-3 rounded-xl text-sm font-medium transition-all active:scale-95"
        >
          {loading ? '...' : 'Enviar'}
        </button>
      </div>
    </div>
  )
}

// ---- Agents Tab ----

function AgentsTab() {
  const [agents, setAgents] = useState<{ name: string; task_type: string; default_provider: string; description: string }[]>([])
  const [selected, setSelected] = useState<string>('')
  const [objective, setObjective] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch('/api/agents').then(r => r.json()).then(d => setAgents(d.agents)).catch(() => {})
  }, [])

  const handleRun = async () => {
    if (!selected || !objective.trim() || loading) return
    setLoading(true)
    setResult('')
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: objective.trim(), agent: selected, use_rag: true }),
      })
      const data = await res.json()
      setResult(data.response || JSON.stringify(data))
    } catch (err) {
      setResult(`Erro: ${err}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Agent list */}
      <div className="lg:col-span-1 space-y-2">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Agentes</h2>
        {agents.map((agent) => (
          <button
            key={agent.name}
            onClick={() => { setSelected(agent.name); setResult('') }}
            className={`w-full text-left p-3 rounded-xl border transition-all ${
              selected === agent.name
                ? 'bg-indigo-600/20 border-indigo-500/30 text-indigo-200'
                : 'bg-gray-800/50 border-gray-700/50 text-gray-300 hover:border-gray-600'
            }`}
          >
            <div className="font-medium text-sm capitalize">{agent.name}</div>
            <div className="text-xs text-gray-500 mt-0.5">{agent.task_type} → {agent.default_provider}</div>
          </button>
        ))}
      </div>

      {/* Agent runner */}
      <div className="lg:col-span-2 space-y-4">
        {selected ? (
          <>
            <div>
              <label className="text-sm text-gray-400 mb-1 block">Objetivo para <span className="text-indigo-300 capitalize">{selected}</span>:</label>
              <textarea
                name="objective"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                rows={3}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500/50"
                placeholder="Descreva o que o agente deve fazer..."
              />
            </div>
            <button
              onClick={handleRun}
              disabled={loading || !objective.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-5 py-2 rounded-xl text-sm font-medium transition-all active:scale-95"
            >
              {loading ? 'Executando...' : 'Executar'}
            </button>
            {result && (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 mt-4">
                <pre className="text-sm text-gray-200 whitespace-pre-wrap font-sans">{result}</pre>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center h-48 text-gray-600 text-sm">
            Selecione um agente ao lado
          </div>
        )}
      </div>
    </div>
  )
}

// ---- History Tab ----

function HistoryTab() {
  const [entries, setEntries] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/history')
      .then(r => r.json())
      .then(d => setEntries(d.history || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleClear = async () => {
    await fetch('/api/history', { method: 'DELETE' })
    setEntries([])
  }

  if (loading) return <div className="text-gray-500 text-sm">Carregando...</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Histórico ({entries.length})</h2>
        {entries.length > 0 && (
          <button onClick={handleClear} className="text-xs text-red-400 hover:text-red-300 transition-colors">Limpar</button>
        )}
      </div>
      {entries.length === 0 ? (
        <div className="text-center py-12 text-gray-600 text-sm">Nenhuma conversa ainda</div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                <span className="bg-gray-700 px-2 py-0.5 rounded">{entry.provider}</span>
                <span className="bg-gray-700 px-2 py-0.5 rounded">{entry.task_type}</span>
                {entry.agent && <span className="bg-indigo-900/50 px-2 py-0.5 rounded">agente: {entry.agent}</span>}
                <span className="ml-auto">{new Date(entry.timestamp * 1000).toLocaleString('pt-BR')}</span>
              </div>
              <p className="text-sm text-gray-300 mb-1"><span className="text-gray-500">Q:</span> {entry.prompt}</p>
              <p className="text-sm text-gray-400"><span className="text-gray-500">R:</span> {entry.response.length > 200 ? entry.response.slice(0, 200) + '...' : entry.response}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---- Monitoring Tab ----

function MonitoringTab() {
  const [health, setHealth] = useState<any>(null)
  const [config, setConfig] = useState<any>(null)
  const [metrics, setMetrics] = useState<any>(null)

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then(setHealth).catch(() => {})
    fetch('/api/config').then(r => r.json()).then(setConfig).catch(() => {})
    fetch('/api/metrics').then(r => r.json()).then(d => setMetrics(d.metrics)).catch(() => {})
  }, [])

  const getMetric = (name: string) => {
    if (!metrics || !metrics[name]) return 0
    return metrics[name].reduce((s: number, m: any) => s + m.value, 0)
  }

  return (
    <div className="space-y-6">
      {/* Health */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Status do Sistema</h2>
        {health ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(health.checks || {}).map(([component, status]) => (
              <div key={component} className={`p-3 rounded-lg border ${status === 'ok' ? 'bg-green-900/20 border-green-500/30' : 'bg-red-900/20 border-red-500/30'}`}>
                <div className="text-xs text-gray-500 capitalize">{component}</div>
                <div className={`text-sm font-medium ${status === 'ok' ? 'text-green-400' : 'text-red-400'}`}>
                  {status === 'ok' ? '✓ Online' : '✗ Offline'}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-600 text-sm">Carregando...</div>
        )}
      </div>

      {/* Metrics summary */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Métricas (acumulado)</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Prompts" value={getMetric('ai_prompts_total')} />
          <MetricCard label="Tokens Input" value={getMetric('ai_tokens_input_total')} />
          <MetricCard label="Tokens Output" value={getMetric('ai_tokens_output_total')} />
          <MetricCard label="Erros" value={getMetric('ai_errors_total')} format="number" />
          <MetricCard label="Custo (USD)" value={getMetric('ai_cost_usd_total')} format="currency" />
          <MetricCard label="Consultas RAG" value={getMetric('ai_rag_queries_total')} />
          <MetricCard label="Chunks RAG" value={getMetric('ai_rag_chunks_total')} />
          <MetricCard label="Iterações Agente" value={getMetric('ai_agent_iterations_total')} />
        </div>
      </div>

      {/* Config */}
      {config && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Configuração</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            <div><span className="text-gray-500">Primary:</span> {config.primary_provider}</div>
            <div><span className="text-gray-500">Local:</span> {config.local_provider}</div>
            <div><span className="text-gray-500">RAG:</span> {config.rag_enabled ? '✓' : '✗'}</div>
            {Object.entries(config.providers || {}).map(([name, info]: [string, any]) => (
              <div key={name}>
                <span className="text-gray-500 capitalize">{name}:</span>{' '}
                {info.model} {info.configured ? '' : '(🔑 faltando)'}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Link to Grafana */}
      <div className="text-center">
        <a
          href="http://localhost:3001"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          📊 Abrir Grafana Dashboard →
        </a>
      </div>
    </div>
  )
}

function MetricCard({ label, value, format = 'number' }: { label: string; value: number; format?: string }) {
  const formatted = format === 'currency'
    ? `$${value.toFixed(4)}`
    : Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1)
  return (
    <div className="bg-gray-900/50 border border-gray-700/30 rounded-lg p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold text-gray-200 mt-0.5">{formatted}</div>
    </div>
  )
}

export default App
