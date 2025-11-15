import { Lock, Eye } from "lucide-react";

const Index = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="text-center max-w-2xl">
        {/* Custom Logo */}
        <img 
          src="/logo.svg" 
          alt="Guardian Agent" 
          className="h-32 w-32 mx-auto mb-8"
        />
        <h1 className="mb-4 text-5xl tracking-tight text-foreground font-medium">
          Guardian Agent
        </h1>
        <p className="text-xl text-muted-foreground mb-12">
          Real-time call monitoring and scam detection
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          <div className="flex flex-col items-center p-6 rounded-lg border border-border bg-card">
            <Eye className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-medium mb-2">Real-Time Monitoring</h3>
            <p className="text-sm text-muted-foreground text-center">
              Continuously analyzes phone conversations for scam indicators
            </p>
          </div>
          
          <div className="flex flex-col items-center p-6 rounded-lg border border-border bg-card">
            <Shield className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-medium mb-2">AI-Powered Detection</h3>
            <p className="text-sm text-muted-foreground text-center">
              Uses advanced AI to identify fraudulent calls and protect users
            </p>
          </div>
          
          <div className="flex flex-col items-center p-6 rounded-lg border border-border bg-card">
            <Lock className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-medium mb-2">Secure & Private</h3>
            <p className="text-sm text-muted-foreground text-center">
              End-to-end encrypted monitoring with complete privacy protection
            </p>
          </div>
        </div>
        
        <p className="mt-12 text-sm text-muted-foreground">
          Monitoring dashboard will be displayed when a call is active
        </p>
      </div>
    </div>
  );
};

export default Index;
