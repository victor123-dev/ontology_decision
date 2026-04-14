import { useState, useEffect } from "react";

const MOBILE_BREAKPOINT = 768;

export function useIsMobile() { const [isMobile, setIsMobile] = useState(
    typeof window !== "undefined" ? window.innerWidth < MOBILE_BREAKPOINT : false
  );

  useEffect(() => { const checkMobile = () => { setIsMobile(window.innerWidth < MOBILE_BREAKPOINT); };

    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile); }, []);

  return isMobile; }
