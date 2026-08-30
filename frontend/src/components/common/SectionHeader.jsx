import React from "react";
import { LiveBadge, DemoBadge } from "./Badge";

export function SectionHeader({ title, description, isLive = false, badgeText, actions }) {
  return (
    <div className="module-header">
      <div className="module-header-info">
        <div className="module-title">
          <span>{title}</span>
          {isLive ? (
            <LiveBadge text={badgeText || "LIVE OCI BACKEND"} />
          ) : (
            <DemoBadge text={badgeText || "DEMO MODULE"} />
          )}
        </div>
        {description && <p className="module-desc">{description}</p>}
      </div>

      {actions && <div className="module-header-actions">{actions}</div>}
    </div>
  );
}
