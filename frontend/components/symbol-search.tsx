"use client";

import { Search } from "lucide-react";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SymbolSearchProps {
  currentSymbol: string;
  onSubmit: (symbol: string) => void;
  disabled?: boolean;
}

export function SymbolSearch({
  currentSymbol,
  onSubmit,
  disabled,
}: SymbolSearchProps) {
  const [value, setValue] = useState(currentSymbol);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const symbol = value.trim().toUpperCase();
    if (symbol) {
      onSubmit(symbol);
    }
  }

  return (
    <form className="flex w-full gap-2 sm:max-w-sm" onSubmit={handleSubmit}>
      <Input
        aria-label="Ticker symbol"
        placeholder="AAPL"
        value={value}
        onChange={(event) => setValue(event.target.value.toUpperCase())}
        disabled={disabled}
      />
      <Button type="submit" disabled={disabled}>
        <Search className="h-4 w-4" />
        Load
      </Button>
    </form>
  );
}
