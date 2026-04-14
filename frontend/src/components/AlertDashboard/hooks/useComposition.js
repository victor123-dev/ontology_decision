import { useState, useRef, useEffect, useCallback } from "react";

export function useComposition({ onCompositionStart,
  onCompositionEnd,
  onChange } = {}) { const [isComposing, setIsComposing] = useState(false);
  const compositionRef = useRef("");
  const valueRef = useRef("");

  const handleCompositionStart = useCallback(() => { setIsComposing(true);
    onCompositionStart?.(); }, [onCompositionStart]);

  const handleCompositionEnd = useCallback(
    (e) => { setIsComposing(false);
      const target = e.target;
      const value = target.value;
      compositionRef.current = "";
      onCompositionEnd?.(value); },
    [onCompositionEnd]
  );

  const handleChange = useCallback(
    (e) => { valueRef.current = e.target.value;
      if (!isComposing) { onChange?.(e); } },
    [isComposing, onChange]
  );

  return { isComposing,
    onCompositionStart: handleCompositionStart,
    onCompositionEnd: handleCompositionEnd,
    onChange: handleChange }; }
