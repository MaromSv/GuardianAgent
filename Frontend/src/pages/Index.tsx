import { Lock, Eye, Shield, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

// For demo: use Vite dev-server proxy at /api → http://127.0.0.1:5000
const BACKEND_BASE_URL = "/api";
const POLL_INTERVAL = 3000; // Check for active calls every 3 seconds

const Index = () => {
  const navigate = useNavigate();
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    const checkForActiveCalls = async () => {
      try {
        setIsChecking(true);
        console.log(`[DEBUG] Checking for active calls at ${BACKEND_BASE_URL}/calls/active`);
        const response = await fetch(`${BACKEND_BASE_URL}/calls/active`);
        
        console.log(`[DEBUG] /calls/active response status: ${response.status}`);
        
        if (response.ok) {
          const data = await response.json();
          console.log("[DEBUG] /calls/active response data:", data);
          
          if (data.call_sid && data.status === "active") {
            // Auto-redirect to monitoring page (no call_sid in URL for demo)
            console.log(`[DEBUG] ✅ Active call detected! Redirecting to: /monitor`);
            navigate(`/monitor`);
          } else {
            console.log("[DEBUG] No active calls found");
          }
        } else {
          console.log("[DEBUG] No active calls (404 or error)");
        }
      } catch (error) {
        console.error("[DEBUG] Error checking for active calls:", error);
      } finally {
        setIsChecking(false);
      }
    };

    // Check immediately
    checkForActiveCalls();
    
    // Then poll periodically
    const interval = setInterval(checkForActiveCalls, POLL_INTERVAL);
    
    return () => clearInterval(interval);
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="text-center max-w-2xl">
        {/* Custom Logo */}
        <img 
          src="/logo_notext.png" 
          alt="Guardian Agent" 
          className="h-40 w-auto mx-auto mb-8"
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
        
        <div className="mt-12 flex items-center justify-center gap-2">
          {isChecking && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
          <p className="text-sm text-muted-foreground">
            {isChecking ? "Checking for active calls..." : "Monitoring dashboard will be displayed when a call is active"}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Index;
