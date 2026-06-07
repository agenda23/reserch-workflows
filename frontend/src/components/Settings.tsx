import * as React from "react"
import { 
  Save, 
  Plus, 
  X, 
  Settings2, 
  Activity, 
  CheckCircle2, 
  XCircle,
  AlertCircle,
  Loader2
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { useToast } from "@/components/ui/toast"

interface SettingsState {
  seed_keywords: string[]
  target_themes: string[]
  ng_keywords: string[]
  similarity_threshold: number
  note_category: string
  quadrant_mode: string
  quadrant_fixed_threshold: number
}

interface TestResultDetail {
  theme: string
  score: number
}

interface TestResult {
  keyword: string
  max_score: number
  is_relevant: boolean
  is_ng_word: boolean
  details: TestResultDetail[]
}

export const Settings: React.FC = () => {
  const [settings, setSettings] = React.useState<SettingsState>({
    seed_keywords: [],
    target_themes: [],
    ng_keywords: [],
    similarity_threshold: 0.55,
    note_category: "technology",
    quadrant_mode: "fixed",
    quadrant_fixed_threshold: 0.5,
  })
  
  // 各タグ追加用の入力文字ステート
  const [seedInput, setSeedInput] = React.useState("")
  const [themeInput, setThemeInput] = React.useState("")
  const [ngInput, setNgInput] = React.useState("")
  
  // 類似度シミュレータ用のステート
  const [testKeyword, setTestKeyword] = React.useState("")
  const [testResult, setTestResult] = React.useState<TestResult | null>(null)
  const [testing, setTesting] = React.useState(false)
  const [saving, setSaving] = React.useState(false)

  const { toast } = useToast()

  // 設定値のロード
  const fetchSettings = async () => {
    try {
      const res = await fetch("/api/settings")
      const json = await res.json()
      setSettings(json)
    } catch (e) {
      toast({
        title: "設定取得失敗",
        description: "システム設定の読み込み中にエラーが発生しました。",
        variant: "destructive"
      })
    }
  }

  React.useEffect(() => {
    fetchSettings()
  }, [])

  // 設定の保存
  const handleSaveSettings = async () => {
    try {
      setSaving(true)
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
      })
      const json = await res.json()
      if (json.status === "success") {
        toast({
          title: "設定保存完了",
          description: "システム設定を保存しました。次回の収集バッチに適用されます。",
          variant: "success"
        })
      }
    } catch (e) {
      toast({
        title: "保存エラー",
        description: "設定の保存に失敗しました。",
        variant: "destructive"
      })
    } finally {
      setSaving(false)
    }
  }

  // 類似度テストの実行
  const handleTestSimilarity = async () => {
    if (!testKeyword.strip) {
      const kw = testKeyword.trim()
      if (!kw) return
    }
    
    try {
      setTesting(true)
      const res = await fetch("/api/settings/test-similarity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: testKeyword.trim() })
      })
      const json = await res.json()
      setTestResult(json)
    } catch (e) {
      toast({
        title: "テストエラー",
        description: "類似度シミュレーションに失敗しました。",
        variant: "destructive"
      })
    } finally {
      setTesting(false)
    }
  }

  // 配列型の項目（タグ）の追加と削除ヘルパー
  const addTag = (field: keyof SettingsState, val: string, setInput: (v: string) => void) => {
    const trimmed = val.trim()
    if (!trimmed) return
    
    const currentList = settings[field] as string[]
    if (currentList.includes(trimmed)) {
      toast({ title: "重複", description: "既に登録されています。" })
      return
    }
    
    setSettings(prev => ({
      ...prev,
      [field]: [...currentList, trimmed]
    }))
    setInput("")
  }

  const removeTag = (field: keyof SettingsState, val: string) => {
    const currentList = settings[field] as string[]
    setSettings(prev => ({
      ...prev,
      [field]: currentList.filter(item => item !== val)
    }))
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      {/* 左〜中サイド：システム設定フォーム（カラム2つ分） */}
      <div className="lg:col-span-2 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-5 w-5 text-primary" />
              システム設定
            </CardTitle>
            <CardDescription>
              キーワード抽出・類似度フィルタリングのパラメーターを設定します。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            
            {/* noteのカテゴリ指定 */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-foreground">note取得カテゴリ</label>
              <select
                value={settings.note_category}
                onChange={(e) => setSettings(prev => ({ ...prev, note_category: e.target.value }))}
                className="w-full bg-secondary/30 border border-white/10 rounded-md h-9 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="tech" className="bg-card text-foreground">テクノロジー (tech)</option>
                <option value="business" className="bg-card text-foreground">ビジネス (business)</option>
                <option value="money" className="bg-card text-foreground">マネー (money)</option>
                <option value="work" className="bg-card text-foreground">ワーク (work)</option>
              </select>
              <p className="text-[11px] text-muted-foreground">noteで収集する人気記事の対象カテゴリを選択します。</p>
            </div>

            {/* 象限分類モード */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-foreground">4象限分類モード</label>
              <select
                value={settings.quadrant_mode}
                onChange={(e) => setSettings(prev => ({ ...prev, quadrant_mode: e.target.value }))}
                className="w-full bg-secondary/30 border border-white/10 rounded-md h-9 px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="fixed" className="bg-card text-foreground">固定閾値（推奨・時系列比較可能）</option>
                <option value="dynamic" className="bg-card text-foreground">動的閾値（バッチデータの平均値）</option>
              </select>
              <p className="text-[11px] text-muted-foreground">
                固定モードでは閾値が一定のため、過去バッチとの象限比較が可能です。
              </p>
            </div>

            {settings.quadrant_mode === "fixed" && (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-sm font-semibold text-foreground">固定象限閾値</label>
                  <span className="font-mono text-sm font-bold text-primary">{settings.quadrant_fixed_threshold.toFixed(2)}</span>
                </div>
                <Slider
                  min={0.3}
                  max={0.7}
                  step={0.05}
                  value={[settings.quadrant_fixed_threshold]}
                  onValueChange={(val) => setSettings(prev => ({ ...prev, quadrant_fixed_threshold: val[0] }))}
                  className="flex-1"
                />
                <p className="text-[11px] text-muted-foreground">
                  正規化スコアがこの値以上で「高」と判定します（デフォルト: 0.5）。
                </p>
              </div>
            )}

            {/* 類似度しきい値 (Slider) */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-sm font-semibold text-foreground">NLP類似度判定しきい値</label>
                <span className="font-mono text-sm font-bold text-primary">{settings.similarity_threshold.toFixed(2)}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs text-muted-foreground">緩い (0.70)</span>
                <Slider
                  min={0.70}
                  max={0.85}
                  step={0.01}
                  value={[settings.similarity_threshold]}
                  onValueChange={(val) => setSettings(prev => ({ ...prev, similarity_threshold: val[0] }))}
                  className="flex-1"
                />
                <span className="text-xs text-muted-foreground">厳格 (0.85)</span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                設定したターゲットテーマにどれだけ意味が近いか（しきい値以上）で、キーワードを通過させる基準を決めます。
              </p>
            </div>

            <hr className="border-white/5" />

            {/* 1. シードキーワード */}
            <div className="space-y-3">
              <label className="text-sm font-semibold text-foreground block">検索用シードキーワード</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="追加するキーワード..."
                  value={seedInput}
                  onChange={(e) => setSeedInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addTag("seed_keywords", seedInput, setSeedInput)}
                  className="bg-secondary/30 border border-white/10 rounded-md h-9 px-3 text-sm text-foreground flex-1 focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <Button size="sm" onClick={() => addTag("seed_keywords", seedInput, setSeedInput)}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5 min-h-[36px] p-2 rounded-md border border-white/5 bg-secondary/10">
                {settings.seed_keywords.length === 0 ? (
                  <span className="text-xs text-muted-foreground self-center px-1">登録されているワードはありません</span>
                ) : (
                  settings.seed_keywords.map(tag => (
                    <span key={tag} className="inline-flex items-center gap-1 bg-primary/20 text-foreground px-2 py-0.5 rounded-full text-xs font-medium border border-primary/30">
                      {tag}
                      <X className="h-3 w-3 hover:text-red-400 cursor-pointer" onClick={() => removeTag("seed_keywords", tag)} />
                    </span>
                  ))
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">Yahoo!サジェスト検索のキーワード収集に使用する、核となるワードです。</p>
            </div>

            {/* 2. ターゲットテーマ */}
            <div className="space-y-3">
              <label className="text-sm font-semibold text-foreground block">ターゲットテーマ（類似度判定のアンカー）</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="追加するテーマ..."
                  value={themeInput}
                  onChange={(e) => setThemeInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addTag("target_themes", themeInput, setThemeInput)}
                  className="bg-secondary/30 border border-white/10 rounded-md h-9 px-3 text-sm text-foreground flex-1 focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <Button size="sm" onClick={() => addTag("target_themes", themeInput, setThemeInput)}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5 min-h-[36px] p-2 rounded-md border border-white/5 bg-secondary/10">
                {settings.target_themes.length === 0 ? (
                  <span className="text-xs text-muted-foreground self-center px-1">登録されているテーマはありません</span>
                ) : (
                  settings.target_themes.map(tag => (
                    <span key={tag} className="inline-flex items-center gap-1 bg-primary/20 text-foreground px-2 py-0.5 rounded-full text-xs font-medium border border-primary/30">
                      {tag}
                      <X className="h-3 w-3 hover:text-red-400 cursor-pointer" onClick={() => removeTag("target_themes", tag)} />
                    </span>
                  ))
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">抽出するキーワードが、これらのテーマのいずれかと類似している必要があります。</p>
            </div>

            {/* 3. NGキーワード */}
            <div className="space-y-3">
              <label className="text-sm font-semibold text-foreground block">NG除外キーワード（ブラックリスト）</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="除外するNGワード..."
                  value={ngInput}
                  onChange={(e) => setNgInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addTag("ng_keywords", ngInput, setNgInput)}
                  className="bg-secondary/30 border border-white/10 rounded-md h-9 px-3 text-sm text-foreground flex-1 focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <Button size="sm" onClick={() => addTag("ng_keywords", ngInput, setNgInput)}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5 min-h-[36px] p-2 rounded-md border border-white/5 bg-secondary/10">
                {settings.ng_keywords.length === 0 ? (
                  <span className="text-xs text-muted-foreground self-center px-1">除外ワードはありません</span>
                ) : (
                  settings.ng_keywords.map(tag => (
                    <span key={tag} className="inline-flex items-center gap-1 bg-red-500/20 text-red-300 px-2 py-0.5 rounded-full text-xs font-medium border border-red-500/20">
                      {tag}
                      <X className="h-3 w-3 hover:text-red-400 cursor-pointer" onClick={() => removeTag("ng_keywords", tag)} />
                    </span>
                  ))
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">これらのワードを含むキーワードは、自動的に除外（ノイズカット）されます。</p>
            </div>

            <hr className="border-white/5" />

            {/* 保存ボタン */}
            <Button 
              onClick={handleSaveSettings} 
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 font-semibold"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  システム設定を保存
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* 右サイド：類似度シミュレータ（1つ分） */}
      <div className="lg:col-span-1 space-y-6">
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              類似度シミュレータ
            </CardTitle>
            <CardDescription>
              入力した単語が、設定したターゲットテーマに合致するか、その場でローカルモデルで判定テストを行います。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <input
                type="text"
                placeholder="テストする言葉（例: Python自動化）"
                value={testKeyword}
                onChange={(e) => setTestKeyword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTestSimilarity()}
                className="bg-secondary/30 border border-white/10 rounded-md h-9 px-3 text-sm text-foreground w-full focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <Button 
                onClick={handleTestSimilarity} 
                disabled={testing || !testKeyword.trim()} 
                variant="outline"
                className="w-full"
              >
                {testing ? "判定中..." : "類似度テストを実行"}
              </Button>
            </div>

            {/* テスト結果の表示 */}
            {testResult && (
              <div className="border border-white/5 bg-secondary/10 rounded-lg p-4 space-y-3 animate-fade-in text-sm">
                
                {/* 採用可否ステータス */}
                <div className="flex items-center gap-2 justify-between pb-2 border-b border-white/5">
                  <span className="font-semibold text-xs text-muted-foreground">総合判定</span>
                  {testResult.is_ng_word ? (
                    <span className="flex items-center gap-1 text-red-400 font-bold text-xs">
                      <XCircle className="h-4 w-4" /> NGワード該当
                    </span>
                  ) : testResult.is_relevant ? (
                    <span className="flex items-center gap-1 text-emerald-400 font-bold text-xs">
                      <CheckCircle2 className="h-4 w-4" /> 採用 (通過)
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-muted-foreground font-bold text-xs">
                      <AlertCircle className="h-4 w-4" /> しきい値未満
                    </span>
                  )}
                </div>

                {/* 最大スコア表示 */}
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">最大類似度スコア</span>
                  <span className={`font-mono font-bold text-base ${
                    testResult.is_relevant && !testResult.is_ng_word ? "text-emerald-400" : "text-muted-foreground"
                  }`}>
                    {testResult.max_score.toFixed(4)}
                  </span>
                </div>

                {/* 各テーマとの類似度内訳 */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-xs font-semibold text-muted-foreground block">テーマ別類似度内訳</span>
                  <div className="space-y-1 max-h-[180px] overflow-y-auto pr-1">
                    {testResult.details.map((detail, index) => (
                      <div key={detail.theme} className="flex justify-between items-center text-xs py-1 border-b border-white/5 last:border-0">
                        <span className="truncate max-w-[140px]">{detail.theme}</span>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-12 bg-secondary rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${index === 0 && testResult.is_relevant ? 'bg-primary' : 'bg-muted-foreground/30'}`}
                              style={{ width: `${Math.max(detail.score * 100, 0)}%` }}
                            />
                          </div>
                          <span className="font-mono text-[10px] w-8 text-right">{detail.score.toFixed(3)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            )}
          </CardContent>
        </Card>
      </div>

    </div>
  )
}
