import * as React from "react"
import { 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine,
  Label
} from "recharts"
import { 
  Play, 
  RefreshCw, 
  Search, 
  TrendingUp, 
  Loader2,
  Sparkles,
  ArrowUpDown
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/toast"

interface TrendData {
  id: number
  date: string
  keyword: string
  x_score: number
  note_score: number
  total_score: number
  status: string
}

interface BatchStatus {
  status: "idle" | "running" | "success" | "failed"
  message: string
  progress: number
  updated_at: string
}

export const Dashboard: React.FC = () => {
  const [data, setData] = React.useState<TrendData[]>([])
  const [filteredData, setFilteredData] = React.useState<TrendData[]>([])
  const [searchTerm, setSearchTerm] = React.useState("")
  const [loading, setLoading] = React.useState(true)
  const [batchStatus, setBatchStatus] = React.useState<BatchStatus>({
    status: "idle",
    message: "待機中",
    progress: 0,
    updated_at: ""
  })
  
  // テーブルのソートステート
  const [sortField, setSortField] = React.useState<keyof TrendData>("total_score")
  const [sortDirection, setSortDirection] = React.useState<"asc" | "desc">("desc")
  
  // グラフクリック時にハイライトされるキーワード
  const [highlightedKeyword, setHighlightedKeyword] = React.useState<string | null>(null)
  
  const { toast } = useToast()

  // トレンドデータの読み込み
  const fetchTrends = async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/trends")
      const json = await res.json()
      if (json.status === "success") {
        setData(json.data)
        setFilteredData(json.data)
      }
    } catch (e) {
      toast({
        title: "データ取得失敗",
        description: "トレンドデータの取得中にエラーが発生しました。",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  // バッチステータスの確認
  const checkBatchStatus = async () => {
    try {
      const res = await fetch("/api/batch-status")
      const json = await res.json()
      if (json.status === "success") {
        setBatchStatus(json.data)
      }
    } catch (e) {
      console.error("バッチステータスの取得失敗", e)
    }
  }

  // 初回ロード
  React.useEffect(() => {
    fetchTrends()
    checkBatchStatus()
  }, [])

  // バッチ実行中のポーリング処理
  React.useEffect(() => {
    let timer: NodeJS.Timeout
    if (batchStatus.status === "running") {
      timer = setInterval(async () => {
        await checkBatchStatus()
      }, 2000)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [batchStatus.status])

  // バッチステータス変化時の処理（完了したら再ロード）
  const prevStatusRef = React.useRef(batchStatus.status)
  React.useEffect(() => {
    if (prevStatusRef.current === "running" && batchStatus.status === "success") {
      toast({
        title: "収集バッチ完了",
        description: "最新のトレンドキーワードが抽出されました！",
        variant: "success"
      })
      fetchTrends()
    } else if (prevStatusRef.current === "running" && batchStatus.status === "failed") {
      toast({
        title: "収集バッチ失敗",
        description: batchStatus.message || "エラーが発生しました。",
        variant: "destructive"
      })
    }
    prevStatusRef.current = batchStatus.status
  }, [batchStatus.status])

  // 検索フィルタリング
  React.useEffect(() => {
    const lower = searchTerm.toLowerCase()
    const filtered = data.filter(item => 
      item.keyword.toLowerCase().includes(lower) || 
      item.status.toLowerCase().includes(lower)
    )
    setFilteredData(filtered)
  }, [searchTerm, data])

  // 手動バッチ起動
  const handleRunBatch = async () => {
    try {
      const res = await fetch("/api/run-batch", { method: "POST" })
      const json = await res.json()
      if (json.status === "success") {
        toast({
          title: "バッチ開始",
          description: "データ収集・分析を開始しました（時間がかかる場合があります）。",
        })
        setBatchStatus(prev => ({ ...prev, status: "running", progress: 5, message: "バッチ実行をスケジュール中..." }))
      } else {
        toast({
          title: "起動失敗",
          description: json.message || "現在実行中の可能性があります。",
          variant: "destructive"
        })
      }
    } catch (e) {
      toast({
        title: "エラー",
        description: "リクエストに失敗しました。",
        variant: "destructive"
      })
    }
  }

  // ソート処理
  const handleSort = (field: keyof TrendData) => {
    const isAsc = sortField === field && sortDirection === "asc"
    const newDir = isAsc ? "desc" : "asc"
    setSortField(field)
    setSortDirection(newDir)

    const sorted = [...filteredData].sort((a, b) => {
      const aVal = a[field]
      const bVal = b[field]

      if (typeof aVal === "string" && typeof bVal === "string") {
        return newDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      } else {
        return newDir === "asc" 
          ? (aVal as number) - (bVal as number) 
          : (bVal as number) - (aVal as number)
      }
    })
    setFilteredData(sorted)
  }

  // グラフドットクリック時のスクロール・ハイライト連携
  const handleScatterClick = (node: any) => {
    if (!node || !node.payload) return
    const kw = node.payload.keyword
    setHighlightedKeyword(kw)
    
    // テーブル行へスクロール
    const rowElement = document.getElementById(`row-${kw}`)
    if (rowElement) {
      rowElement.scrollIntoView({ behavior: "smooth", block: "center" })
      
      // 数秒後にハイライトを消す
      setTimeout(() => {
        setHighlightedKeyword(null)
      }, 3000)
    }
  }

  // グラフ用のデータフォーマット
  const chartData = filteredData.map(item => ({
    x: item.x_score,
    y: item.note_score,
    keyword: item.keyword,
    total_score: item.total_score,
    status: item.status
  }))

  // カスタムツールチップ
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="rounded-lg border border-white/10 bg-card/90 backdrop-blur-md p-3 text-xs shadow-xl space-y-1">
          <p className="font-bold text-sm text-primary">{data.keyword}</p>
          <p><span className="text-muted-foreground">分類:</span> {data.status}</p>
          <p><span className="text-muted-foreground">X (バズ) スコア:</span> {data.x.toFixed(4)}</p>
          <p><span className="text-muted-foreground">note (需要) スコア:</span> {data.y.toFixed(4)}</p>
          <p className="border-t border-white/5 pt-1 mt-1 font-bold">
            <span className="text-muted-foreground">総合スコア:</span> {data.total_score.toFixed(4)}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      {/* 左サイド：収集コントロール ＆ 進捗 */}
      <div className="lg:col-span-1 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              バッチコントロール
            </CardTitle>
            <CardDescription>Xとnoteのデータを今すぐ収集・分析します。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Button 
                onClick={handleRunBatch} 
                disabled={batchStatus.status === "running"}
                className="w-full flex items-center justify-center gap-2 font-semibold"
              >
                {batchStatus.status === "running" ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    収集処理中...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-current" />
                    データ収集・分析を実行
                  </>
                )}
              </Button>
              <Button 
                variant="outline" 
                size="icon" 
                onClick={fetchTrends}
                disabled={batchStatus.status === "running" || loading}
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>

            {/* バッチステータス詳細表示 */}
            <div className="border border-white/5 bg-secondary/20 rounded-lg p-4 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-muted-foreground">現在の状況</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  batchStatus.status === "running" ? "bg-amber-500/20 text-amber-300 animate-pulse" :
                  batchStatus.status === "success" ? "bg-emerald-500/20 text-emerald-300" :
                  batchStatus.status === "failed" ? "bg-red-500/20 text-red-300" :
                  "bg-muted/30 text-muted-foreground"
                }`}>
                  {batchStatus.status === "running" ? "実行中" :
                   batchStatus.status === "success" ? "完了" :
                   batchStatus.status === "failed" ? "エラー" : "待機中"}
                </span>
              </div>
              <p className="text-sm font-medium">{batchStatus.message || "待機中"}</p>
              
              {batchStatus.status === "running" && (
                <div className="space-y-1 pt-1">
                  <div className="h-2 w-full bg-secondary/80 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary transition-all duration-500" 
                      style={{ width: `${batchStatus.progress}%` }}
                    />
                  </div>
                  <div className="flex justify-end text-[10px] text-muted-foreground">
                    {batchStatus.progress}%
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 右サイド（2/3）：4象限グラフ */}
      <div className="lg:col-span-2">
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              トレンド分析マトリクス
            </CardTitle>
            <CardDescription>
              横軸：Xバズ（瞬発力） ｜ 縦軸：note需要（深さ）の4象限プロット。ドットをクリックすると下の表へ移動します。
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart
                margin={{ top: 20, right: 30, bottom: 20, left: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  type="number" 
                  dataKey="x" 
                  name="X Score" 
                  domain={[0, 1.05]} 
                  stroke="rgba(255,255,255,0.4)"
                  tick={{ fontSize: 10 }}
                >
                  <Label value="Xバズ（話題の広さ）" offset={-10} position="insideBottom" fill="rgba(255,255,255,0.6)" fontSize={11} />
                </XAxis>
                <YAxis 
                  type="number" 
                  dataKey="y" 
                  name="note Score" 
                  domain={[0, 1.05]}
                  stroke="rgba(255,255,255,0.4)"
                  tick={{ fontSize: 10 }}
                >
                  <Label value="note需要（関心の深さ）" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="rgba(255,255,255,0.6)" fontSize={11} />
                </YAxis>
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.2)' }} />
                
                {/* 4象限を分ける基準線（平均値目安） */}
                <ReferenceLine x={0.5} stroke="rgba(255,255,255,0.15)" strokeDasharray="5 5" />
                <ReferenceLine y={0.5} stroke="rgba(255,255,255,0.15)" strokeDasharray="5 5" />
                
                <Scatter 
                  name="Keywords" 
                  data={chartData} 
                  fill="#6366f1" 
                  cursor="pointer"
                  onClick={handleScatterClick}
                  // ドットのスタイル調整
                  shape={(props: any) => {
                    const { cx, cy } = props;
                    return (
                      <circle 
                        cx={cx} 
                        cy={cy} 
                        r={6} 
                        fill="hsl(var(--primary))" 
                        stroke="rgba(255,255,255,0.5)" 
                        strokeWidth={1}
                        className="transition-all hover:scale-150 duration-200"
                      />
                    );
                  }}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* 下部：詳細データテーブル（全幅） */}
      <div className="lg:col-span-3">
        <Card>
          <CardHeader className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <CardTitle>キーワード詳細データ</CardTitle>
              <CardDescription>抽出・スコアリングされた全キーワードの明細リストです。</CardDescription>
            </div>
            {/* 検索フォーム */}
            <div className="relative w-full md:max-w-xs">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="キーワード検索..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 w-full bg-secondary/30 border border-white/10 rounded-md h-9 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
          </CardHeader>
          <CardContent className="p-0 max-h-[400px] overflow-y-auto relative">
            <Table>
              <TableHeader className="sticky top-0 bg-card/90 backdrop-blur-md z-10 shadow-sm border-b">
                <TableRow>
                  <TableHead className="w-[40%] cursor-pointer hover:text-foreground" onClick={() => handleSort("keyword")}>
                    キーワード <ArrowUpDown className="inline h-3 w-3 ml-1" />
                  </TableHead>
                  <TableHead className="w-[15%] cursor-pointer hover:text-foreground text-right" onClick={() => handleSort("total_score")}>
                    総合スコア <ArrowUpDown className="inline h-3 w-3 ml-1" />
                  </TableHead>
                  <TableHead className="w-[15%] cursor-pointer hover:text-foreground text-right" onClick={() => handleSort("x_score")}>
                    Xバズ <ArrowUpDown className="inline h-3 w-3 ml-1" />
                  </TableHead>
                  <TableHead className="w-[15%] cursor-pointer hover:text-foreground text-right" onClick={() => handleSort("note_score")}>
                    note需要 <ArrowUpDown className="inline h-3 w-3 ml-1" />
                  </TableHead>
                  <TableHead className="w-[15%] cursor-pointer hover:text-foreground" onClick={() => handleSort("status")}>
                    分類 <ArrowUpDown className="inline h-3 w-3 ml-1" />
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center h-24 text-muted-foreground">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                      読み込み中...
                    </TableCell>
                  </TableRow>
                ) : filteredData.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center h-24 text-muted-foreground">
                      データがありません。収集バッチを実行してください。
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredData.map((item) => (
                    <TableRow 
                      key={item.id}
                      id={`row-${item.keyword}`}
                      className={`transition-all duration-500 border-white/5 ${
                        highlightedKeyword === item.keyword 
                          ? "bg-primary/20 hover:bg-primary/20 scale-[0.99] font-bold" 
                          : "hover:bg-secondary/40"
                      }`}
                    >
                      <TableCell className="font-semibold text-foreground">{item.keyword}</TableCell>
                      <TableCell className="text-right font-mono text-primary font-bold">{item.total_score.toFixed(4)}</TableCell>
                      <TableCell className="text-right font-mono">{item.x_score.toFixed(4)}</TableCell>
                      <TableCell className="text-right font-mono">{item.note_score.toFixed(4)}</TableCell>
                      <TableCell>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          item.status.includes("第1") ? "bg-primary/25 text-primary-foreground border border-primary/30" :
                          item.status.includes("第2") ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/20" :
                          item.status.includes("第4") ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/20" :
                          "bg-muted/40 text-muted-foreground"
                        }`}>
                          {item.status}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

    </div>
  )
}
