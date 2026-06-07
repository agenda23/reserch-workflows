import * as React from "react"
import { Sparkles, LayoutDashboard, Settings as SettingsIcon } from "lucide-react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ToastProvider } from "@/components/ui/toast"
import { Dashboard } from "@/components/Dashboard"
import { Settings } from "@/components/Settings"

function AppContent() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl min-h-screen flex flex-col justify-between">
      
      {/* プレミアム・ヘッダー */}
      <header className="mb-8 border border-white/10 bg-card/20 backdrop-blur-xl rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="bg-primary/20 p-2.5 rounded-xl border border-primary/30 flex items-center justify-center">
            <Sparkles className="h-6 w-6 text-primary animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-bold tracking-tight text-foreground bg-gradient-to-r from-white via-slate-100 to-primary bg-clip-text text-transparent">
              Trend Keywords Extractor & Analyzer
            </h1>
            <p className="text-xs md:text-sm text-muted-foreground mt-0.5">
              Xの話題性とnoteのコンテンツ需要を掛け合わせる、データ駆動型のトレンド発掘ダッシュボード
            </p>
          </div>
        </div>
      </header>

      {/* タブメインエリア */}
      <main className="flex-grow">
        <Tabs defaultValue="dashboard" className="w-full space-y-6">
          <div className="flex justify-between items-center border-b border-white/5 pb-2">
            <TabsList>
              <TabsTrigger value="dashboard" className="flex items-center gap-2">
                <LayoutDashboard className="h-4 w-4" />
                ダッシュボード
              </TabsTrigger>
              <TabsTrigger value="settings" className="flex items-center gap-2">
                <SettingsIcon className="h-4 w-4" />
                システム設定
              </TabsTrigger>
            </TabsList>
            <div className="text-[11px] text-muted-foreground hidden sm:block">
              Powered by Sentence Transformers & FastAPI
            </div>
          </div>

          <TabsContent value="dashboard" className="outline-none">
            <Dashboard />
          </TabsContent>
          
          <TabsContent value="settings" className="outline-none">
            <Settings />
          </TabsContent>
        </Tabs>
      </main>

      {/* フッター */}
      <footer className="mt-12 py-6 border-t border-white/5 text-center text-xs text-muted-foreground">
        &copy; {new Date().getFullYear()} Trend Keywords Automated Analysis System. All rights reserved.
      </footer>
      
    </div>
  )
}

function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  )
}

export default App
