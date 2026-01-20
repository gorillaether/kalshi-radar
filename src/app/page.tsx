'use client'

import { useState, useEffect } from 'react'

interface Opportunity {
  ticker: string
  title: string
  series_ticker: string
  category: string
  inefficiency_score: number
  spread_pct: number
  mid_price: number
  yes_bid: number
  yes_ask: number
  open_interest: number
  volume_24h: number
  last_price: number
  analysis: string
  is_opportunity: boolean
}

interface OpportunitiesData {
  opportunities: Opportunity[]
  count: number
  series_checked: number
}

const API_URL = 'https://kalshi-radar-api-487452617539.us-central1.run.app'

const categoryColors: Record<string, string> = {
  'Politics': 'bg-yellow-100 text-yellow-900',
  'Economics': 'bg-blue-100 text-blue-900',
  'Crypto': 'bg-purple-100 text-purple-900',
  'Climate and Weather': 'bg-green-100 text-green-900',
  'Sports': 'bg-red-100 text-red-900',
  'Entertainment': 'bg-pink-100 text-pink-900',
}

export default function Home() {
  const [data, setData] = useState<OpportunitiesData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const fetchOpportunities = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_URL}/api/opportunities?limit=50`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const result = await response.json()
      setData(result)
      setLastUpdate(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOpportunities()
    const interval = setInterval(fetchOpportunities, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const categories = data ? ['all', ...new Set(data.opportunities.map(o => o.category))] : ['all']
  
  const filteredOpportunities = data?.opportunities.filter(
    opp => selectedCategory === 'all' || opp.category === selectedCategory
  ) || []

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">🎯 Kalshi Radar</h1>
          <p className="text-gray-600 text-lg mb-4">
            Discover mispriced prediction markets with actionable trading edges. We continuously scan Kalshi to find 
            wide bid-ask spreads on liquid, actively-traded contracts where market makers haven't tightened pricing yet.
          </p>

          {/* Methodology */}
          <details className="mt-4">
            <summary className="cursor-pointer text-indigo-600 font-semibold hover:text-indigo-800">
              📊 How We Find Opportunities
            </summary>
            <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-3 text-sm">
              <p className="font-semibold text-gray-900">We filter for markets that pass all three checks:</p>
              
              <div className="pl-4 border-l-4 border-indigo-600">
                <p className="font-semibold text-indigo-900">1. Wide Spread (&gt;5%)</p>
                <p className="text-gray-700">The gap between bid and ask prices indicates mispricing</p>
              </div>
              
              <div className="pl-4 border-l-4 border-purple-600">
                <p className="font-semibold text-purple-900">2. Real Liquidity (&gt;50 contracts)</p>
                <p className="text-gray-700">Enough open interest to actually enter and exit positions</p>
              </div>
              
              <div className="pl-4 border-l-4 border-green-600">
                <p className="font-semibold text-green-900">3. Active Trading (&gt;5 contracts/day)</p>
                <p className="text-gray-700">Recent volume confirms this is a real market, not a dead listing</p>
              </div>
              
              <div className="bg-yellow-50 border-l-4 border-yellow-500 p-3 rounded">
                <p className="font-semibold text-yellow-900">Focus on the spread percentage</p>
                <p className="text-gray-700 mt-1">
                  A 10% spread means you could potentially buy at 60¢ and sell at 66¢ for a 10% profit 
                  (minus fees). Higher spreads = bigger potential edge.
                </p>
              </div>
            </div>
          </details>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="text-sm text-gray-500 mb-2">Opportunities Found</div>
            <div className="text-3xl font-bold text-gray-900">{data?.count || '-'}</div>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="text-sm text-gray-500 mb-2">Series Scanned</div>
            <div className="text-3xl font-bold text-gray-900">{data?.series_checked || '-'}</div>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="text-sm text-gray-500 mb-2">Last Updated</div>
            <div className="text-xl font-bold text-gray-900">
              {lastUpdate ? lastUpdate.toLocaleTimeString() : '-'}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <div className="flex flex-wrap items-center gap-4">
            <span className="font-semibold text-gray-700">Filter by Category:</span>
            <div className="flex flex-wrap gap-2">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-4 py-2 rounded-lg font-medium transition-all ${
                    selectedCategory === cat
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                {cat === 'all' ? 'All' : cat}
                </button>
              ))}
            </div>
            <button
              onClick={fetchOpportunities}
              disabled={loading}
              className="ml-auto px-6 py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-gray-400 transition-all"
            >
              {loading ? 'Refreshing...' : 'Refresh Data'}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-100 border-2 border-red-500 rounded-xl p-6 mb-8 text-red-900">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Loading */}
        {loading && !data && (
          <div className="text-center text-white text-xl py-12">
            Loading opportunities...
          </div>
        )}

        {/* Opportunities */}
        <div className="space-y-6">
          {filteredOpportunities.map((opp) => (
            <div key={opp.ticker} className="bg-white rounded-xl shadow-lg p-6 hover:shadow-2xl transition-shadow">
              {/* Header */}
              <div className="flex items-start justify-between mb-4 gap-4">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{opp.title}</h3>
                  <p className="text-sm text-gray-500 font-mono">{opp.ticker} • {opp.series_ticker}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                    categoryColors[opp.category] || 'bg-gray-100 text-gray-900'
                  }`}>
                    {opp.category}
                  </span>
                  <div className="text-right">
                    <div className="text-xs text-gray-500 uppercase tracking-wide">Spread</div>
                    <div className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                      {opp.spread_pct.toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-indigo-50 rounded-lg p-3 border-2 border-indigo-200">
                  <div className="text-xs text-indigo-600 uppercase tracking-wide mb-1 font-semibold">Spread</div>
                  <div className="text-xl font-bold text-indigo-900">{opp.spread_pct.toFixed(1)}%</div>
                  <div className="text-xs text-indigo-600 mt-1">Your potential edge</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Open Interest</div>
                  <div className="text-lg font-bold text-gray-900">{opp.open_interest.toLocaleString()}</div>
                  <div className="text-xs text-gray-600 mt-1">Total contracts</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">24h Volume</div>
                  <div className="text-lg font-bold text-gray-900">{opp.volume_24h.toLocaleString()}</div>
                  <div className="text-xs text-gray-600 mt-1">Traded today</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Mid Price</div>
                  <div className="text-lg font-bold text-gray-900">{opp.mid_price.toFixed(1)}¢</div>
                  <div className="text-xs text-gray-600 mt-1">Fair value</div>
                </div>
              </div>

              {/* Price Info */}
              <div className="flex gap-4 bg-gray-50 rounded-lg p-4 mb-4">
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-1">YES Bid</div>
                  <div className="text-2xl font-bold text-green-600">{opp.yes_bid}¢</div>
                </div>
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-1">YES Ask</div>
                  <div className="text-2xl font-bold text-red-600">{opp.yes_ask}¢</div>
                </div>
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-1">Last Trade</div>
                  <div className="text-2xl font-bold text-gray-900">{opp.last_price}¢</div>
                </div>
              </div>

              {/* Analysis */}
              <div className="bg-yellow-50 border-l-4 border-yellow-500 rounded p-4 text-yellow-900">
                {opp.analysis}
              </div>
            </div>
          ))}
        </div>

        {filteredOpportunities.length === 0 && !loading && (
          <div className="text-center text-white text-xl py-12">
            No opportunities found for this category.
          </div>
        )}
      </div>
    </div>
  )
}
