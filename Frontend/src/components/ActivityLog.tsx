import { GuardianAgentState } from "@/types/guardian";
import { Activity } from "lucide-react";

interface ActivityLogProps {
  state: GuardianAgentState | null;
}

export function ActivityLog({ state }: ActivityLogProps) {
  const activities = state?.activity || [];

  if (activities.length === 0) {
    return (
      <div className="bg-card rounded-lg border border-border p-6">
        <h3 className="text-lg tracking-tight text-foreground mb-4">Activity Log</h3>
        <p className="text-base text-muted-foreground">No activity recorded yet</p>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <h3 className="text-lg tracking-tight text-foreground mb-4">Activity Log</h3>
      
      <div className="space-y-3">
        {activities.map((activity, index) => (
          <div key={index} className="flex items-start gap-3 pb-3 border-b border-border last:border-0">
            <Activity className="h-5 w-5 text-guardian-blue mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-base font-medium text-foreground capitalize">{activity.stage}</p>
              {activity.data && (
                <p className="text-sm text-muted-foreground mt-1">
                  {typeof activity.data === "object" 
                    ? JSON.stringify(activity.data, null, 2)
                    : String(activity.data)
                  }
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
