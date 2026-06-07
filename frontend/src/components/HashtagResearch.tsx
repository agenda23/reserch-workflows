import * as React from "react"
import { Hash, BarChart3, TrendingUp, Clock, Loader2 } from "lucide-react"
import { LineChart, Line, ResponsiveContainer } from "recharts"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { useToast } from "@/components/ui/toast"

interface HashtagDiff {
  new: string[]
  removed: string[]
  stable: string[]
  post_count_delta: number
  post_count_delta_pct: number
}

interface HashtagData {
  hashtag: string
  post_count: number
  related_tags: string[]
  updated_at: string
  diff?: HashtagDiff
}

interface CooccurrenceItem {
  tag: string
  seed: string
  weighted_demand: number
  article_count: number
  status: "new" | "up" | "stable" | "down"
}

interface HistoryPoint {
  batch_date: string
  post_count: number
  related_tags: string[]
}

const STATUS_LABEL: Record<string, { label: string; className: string }> = {
  new: { label: "🆕", className: "text-emerald-600 font-bold" },
  up: { label: "↑", className: "text-emerald-600 font-bold" },
  stable: { label: "→", className: "text-muted-foreground" },
  down: { label: "↓", className: "text-muted-foreground/60" },
}

function formatDelta(pct: number | undefined): string {
  if (pct === undefined || pct === 0) return "→+0.0%"
  const sign = pct > 0 ? "↑" : "↓"
  return `${sign}${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`
}

function deltaColor(pct: number | undefined): string {
  if (!pct || Math.abs(pct) < 0.5) return "text-muted-foreground"
  return pct > 0 ? "text-emerald-600" : "text-red-500"
}

function MiniSparkline({ data }: { data: HistoryPoint[] }) {
  const chartData = [...data].reverse().map(d => ({ date: d.batch_date, count: d.post_count }))
  if (chartData.length < 2) {
    return <span className="text-[10px] text-muted-foreground">履歴不足</span>
  }
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={chartData}>
        <Line type="monotone" dataKey="count" stroke="hsl(var(--primary))" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export const HashtagResearch: React.FC = () => {
  const [hashtags, setHashtags] = React.useState<HashtagData[]>([])
  const [cooccurrence, setCooccurrence] = React.useState<Record<string, CooccurrenceItem[]>>({})
  const [histories, setHistories] = React.useState<Record<string, HistoryPoint[]>>({})
  const [loading, setLoading] = React.useState(false)
  const [seedFilter, setSeedFilter] = React.useState<string>("all")
  const [sortMode, setSortMode] = React.useState<"demand" | "new">("demand")
  const { toast } = useToast()

  const fetchAll = async () => {
    try {
      setLoading(true)
      const [hashtagRes, coocRes] = await Promise.all([
        fetch("/api/note-hashtags?with_diff=true"),
        fetch("/api/hashtag-cooccurrence"),
      ])
      const hashtagJson = await hashtagRes.json()
      const coocJson = await coocRes.json()
      if (hashtagJson.status === "success") setHashtags(hashtagJson.data)
      if (coocJson.status === "success") setCooccurrence(coocJson.data)
    } catch {
      toast({
        title: "データ取得失敗",
        description: "ハッシュタグ統計データの読み込み中にエラーが発生しました。",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const fetchHistories = async (tags: string[]) => {
    const results: Record<string, HistoryPoint[]> = {}
    await Promise.all(
      tags.map(async (tag) => {
        try {
          const res = await fetch(`/api/hashtag-history/${encodeURIComponent(tag)}?limit=8`)
          const json = await res.json()
          if (json.status === "success") results[tag] = json.data
        } catch { /* ignore */ }
      })
    )
    setHistories(results)
  }

  React.useEffect(() => { fetchAll() }, [])

  React.useEffect(() => {
    if (hashtags.length > 0) {
      fetchHistories(hashtags.map(h => h.hashtag))
    }
  }, [hashtags])

  const seeds = React.useMemo(() => Object.keys(cooccurrence), [cooccurrence])

  const risingWords = React.useMemo(() => {
    let items: CooccurrenceItem[] = Object.values(cooccurrence).flat()
    if (seedFilter !== "all") {
      items = items.filter(i => i.seed === seedFilter)
    }
    if (sortMode === "new") {
      const order = { new: 0, up: 1, stable: 2, down: 3 }
      items.sort((a, b) => (order[a.status] - order[b.status]) || (b.weighted_demand - a.weighted_demand))
    } else {
      items.sort((a, b) => b.weighted_demand - a.weighted_demand)
    }
    return items
  }, [cooccurrence, seedFilter, sortMode])

  const totalPostCount = hashtags.reduce((acc, h) => acc + h.post_count, 0)
  const totalDeltaPct = hashtags.length > 0 && hashtags[0].diff
    ? hashtags.reduce((acc, h) => acc + (h.diff?.post_count_delta_pct ?? 0), 0) / hashtags.length
    : undefined
  const topHashtag = hashtags[0]

  return (
    <div className="space-y-6">
      {/* 概要カード */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">監視中ハッシュタグ総数</CardDescription>
            <CardTitle className="text-3xl font-extrabold text-primary flex items-baseline gap-2">
              {hashtags.length} <span className="text-sm font-normal text-muted-foreground">件</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground font-medium">シードキーワードに基づき取得</p>
          </CardContent>
        </Card>

        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">最大投稿ボリューム</CardDescription>
            <CardTitle className="text-3xl font-extrabold text-emerald-600 flex items-baseline gap-2">
              {topHashtag ? topHashtag.post_count.toLocaleString() : 0}
              <span className="text-sm font-normal text-muted-foreground">件</span>
              {topHashtag?.diff && (
                <span className={`text-sm font-mono font-bold ${deltaColor(topHashtag.diff.post_count_delta_pct)}`}>
                  {formatDelta(topHashtag.diff.post_count_delta_pct)}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground font-medium">
              #{topHashtag?.hashtag ?? "N/A"}（先週比）
            </p>
          </CardContent>
        </Card>

        <Card className="bg-card border-border shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">総投稿ボリューム</CardDescription>
            <CardTitle className="text-3xl font-extrabold text-sky-600 flex items-baseline gap-2">
              {totalPostCount.toLocaleString()}
              <span className="text-sm font-normal text-muted-foreground">件</span>
              {totalDeltaPct !== undefined && (
                <span className={`text-sm font-mono font-bold ${deltaColor(totalDeltaPct)}`}>
                  {formatDelta(totalDeltaPct)}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground font-medium">シードタグ全体の累積投稿数</p>
          </CardContent>
        </Card>
      </div>

      {/* 3タブ構成 */}
      <Tabs defaultValue="rising">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="rising" className="flex items-center gap-1.5">
            <TrendingUp className="h-4 w-4" /> 浮上ワード
          </TabsTrigger>
          <TabsTrigger value="stats" className="flex items-center gap-1.5">
            <Hash className="h-4 w-4" /> タグ統計
          </TabsTrigger>
          <TabsTrigger value="changelog" className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" /> 変化ログ
          </TabsTrigger>
        </TabsList>

        {/* タブ① 浮上ワード */}
        <TabsContent value="rising">
          <Card>
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <CardTitle>浮上ワード</CardTitle>
                  <CardDescription>人気記事でシードタグと共起するキーワード（スキ数加重）</CardDescription>
                </div>
                <div className="flex gap-2">
                  <select
                    value={seedFilter}
                    onChange={e => setSeedFilter(e.target.value)}
                    className="h-8 text-xs border border-border rounded px-2 bg-background"
                  >
                    <option value="all">全シード</option>
                    {seeds.map(s => <option key={s} value={s}>#{s}</option>)}
                  </select>
                  <select
                    value={sortMode}
                    onChange={e => setSortMode(e.target.value as "demand" | "new")}
                    className="h-8 text-xs border border-border rounded px-2 bg-background"
                  >
                    <option value="demand">共起需要順</option>
                    <option value="new">新着優先</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="py-12 text-center text-muted-foreground flex items-center justify-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" /> 読み込み中...
                </div>
              ) : risingWords.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  データがありません。バッチを2回以上実行すると差分が表示されます。
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground font-bold text-xs">
                        <th className="py-2 px-3 text-left w-8">#</th>
                        <th className="py-2 px-3 text-left">キーワード</th>
                        <th className="py-2 px-3 text-left">起点タグ</th>
                        <th className="py-2 px-3 text-right">共起需要</th>
                        <th className="py-2 px-3 text-right">記事数</th>
                        <th className="py-2 px-3 text-center w-12">状態</th>
                      </tr>
                    </thead>
                    <tbody>
                      {risingWords.map((item, idx) => (
                        <tr key={`${item.seed}-${item.tag}`} className={`border-b border-border hover:bg-muted/30 ${item.status === "down" ? "opacity-50" : ""}`}>
                          <td className="py-2.5 px-3 text-muted-foreground font-mono text-xs">{idx + 1}</td>
                          <td className="py-2.5 px-3 font-semibold whitespace-nowrap">{item.tag}</td>
                          <td className="py-2.5 px-3 text-primary text-xs whitespace-nowrap">#{item.seed}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-600 whitespace-nowrap">{item.weighted_demand.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-muted-foreground whitespace-nowrap">{item.article_count}件</td>
                          <td className={`py-2.5 px-3 text-center ${STATUS_LABEL[item.status]?.className ?? ""}`}>
                            {STATUS_LABEL[item.status]?.label ?? "→"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="text-[11px] text-muted-foreground mt-4 px-3">
                    「共起需要」= このキーワードと一緒に登場した note 人気記事のスキ数合計
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* タブ② タグ統計 */}
        <TabsContent value="stats">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Hash className="h-5 w-5 text-primary" /> note ハッシュタグ需要調査
                </CardTitle>
                <CardDescription>投稿件数・関連タグの変化</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="py-12 text-center text-muted-foreground">読み込み中...</div>
                ) : hashtags.length === 0 ? (
                  <div className="py-12 text-center text-sm text-muted-foreground">データがありません。</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[760px] text-sm">
                      <thead>
                        <tr className="border-b border-border text-muted-foreground font-bold text-xs">
                          <th className="py-3 px-3">タグ名</th>
                          <th className="py-3 px-3 text-right">note件数</th>
                          <th className="py-3 px-3">関連タグ</th>
                          <th className="py-3 px-3 text-right">更新</th>
                        </tr>
                      </thead>
                      <tbody>
                        {hashtags.map(h => (
                          <tr key={h.hashtag} className="border-b border-border hover:bg-muted/40">
                            <td className="py-3 px-3 font-bold whitespace-nowrap">
                              <span className="text-primary">#</span>{h.hashtag}
                            </td>
                            <td className="py-3 px-3 text-right whitespace-nowrap">
                              <span className="font-mono font-bold text-emerald-600">{h.post_count.toLocaleString()}</span>
                              {h.diff && (
                                <span className={`ml-1.5 text-[10px] font-mono ${deltaColor(h.diff.post_count_delta_pct)}`}>
                                  {formatDelta(h.diff.post_count_delta_pct)}
                                </span>
                              )}
                            </td>
                            <td className="py-3 px-3">
                              <div className="flex flex-wrap gap-1 items-center">
                                {h.diff && h.diff.new.length > 0 && (
                                  <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-200 font-bold">
                                    🆕{h.diff.new.length}件
                                  </span>
                                )}
                                {h.diff && h.diff.removed.length > 0 && (
                                  <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded border border-gray-200">
                                    💀{h.diff.removed.length}件
                                  </span>
                                )}
                                {h.related_tags.slice(0, 5).map(rt => (
                                  <span key={rt} className="bg-muted text-[10px] px-1.5 py-0.5 rounded border border-border">#{rt}</span>
                                ))}
                                {h.related_tags.length > 5 && (
                                  <span className="text-[10px] text-muted-foreground">+{h.related_tags.length - 5}</span>
                                )}
                              </div>
                            </td>
                            <td className="py-3 px-3 text-right text-xs text-muted-foreground font-mono whitespace-nowrap">
                              {h.updated_at ? h.updated_at.split(" ")[1] || h.updated_at : "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" /> ボリューム比率
                </CardTitle>
                <CardDescription>note投稿件数の比率</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {hashtags.map((h, index) => {
                  const maxCount = hashtags[0]?.post_count ?? 1
                  return (
                    <div key={h.hashtag} className="space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold">#{h.hashtag}</span>
                        <span className="font-mono text-muted-foreground">{h.post_count.toLocaleString()}</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden border border-border">
                        <div
                          className={`h-full rounded-full ${index === 0 ? "bg-emerald-500" : "bg-emerald-500/60"}`}
                          style={{ width: `${(h.post_count / maxCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* タブ③ 変化ログ */}
        <TabsContent value="changelog">
          <div className="space-y-4">
            {loading ? (
              <div className="py-12 text-center text-muted-foreground">読み込み中...</div>
            ) : hashtags.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                データがありません。バッチを2回以上実行すると変化ログが表示されます。
              </div>
            ) : (
              hashtags.map(h => {
                const diff = h.diff
                const history = histories[h.hashtag] ?? []
                return (
                  <Card key={h.hashtag}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base flex items-center gap-2">
                        <span className="text-primary">#</span>{h.hashtag}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-2 flex-wrap">
                        <span>投稿件数: <strong>{h.post_count.toLocaleString()}件</strong></span>
                        {diff && diff.post_count_delta !== 0 && (
                          <span className={`font-mono text-xs font-bold ${deltaColor(diff.post_count_delta_pct)}`}>
                            ({diff.post_count_delta > 0 ? "↑" : "↓"}{Math.abs(diff.post_count_delta).toLocaleString()} 先週比 {formatDelta(diff.post_count_delta_pct)})
                          </span>
                        )}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="max-w-xs">
                        <p className="text-[10px] text-muted-foreground mb-1">投稿件数推移（過去8バッチ）</p>
                        <MiniSparkline data={history} />
                      </div>

                      {diff && diff.new.length > 0 && (
                        <div>
                          <p className="text-xs font-bold text-emerald-600 mb-1.5">🆕 新出現（今回初めて登場）</p>
                          <div className="flex flex-wrap gap-1.5">
                            {diff.new.map(t => (
                              <span key={t} className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">{t}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {diff && diff.stable.length > 0 && (
                        <div>
                          <p className="text-xs font-bold text-muted-foreground mb-1.5">↗ 継続（先週から引き続き）</p>
                          <div className="flex flex-wrap gap-1.5">
                            {diff.stable.map(t => (
                              <span key={t} className="text-xs bg-muted px-2 py-0.5 rounded border border-border">{t}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {diff && diff.removed.length > 0 && (
                        <div>
                          <p className="text-xs font-bold text-gray-400 mb-1.5">💀 消滅（先週はあったが今週なし）</p>
                          <div className="flex flex-wrap gap-1.5">
                            {diff.removed.map(t => (
                              <span key={t} className="text-xs bg-gray-50 text-gray-400 px-2 py-0.5 rounded border border-gray-200 line-through">{t}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {(!diff || (diff.new.length === 0 && diff.removed.length === 0 && diff.stable.length === 0)) && (
                        <p className="text-xs text-muted-foreground">前回バッチとの比較データがありません（2回以上バッチ実行が必要です）</p>
                      )}
                    </CardContent>
                  </Card>
                )
              })
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
