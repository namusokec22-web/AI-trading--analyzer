
# Vision module contract

Input: chart screenshot.

Return ONLY JSON:
{
  "symbol": null,
  "timeframe": null,
  "visible_price": null,
  "trend": "bullish|bearish|mixed|unclear",
  "market_structure": "string",
  "support_levels": [],
  "resistance_levels": [],
  "setup": "string",
  "confirmation_present": null,
  "invalidation": "string",
  "quality": "good|limited|poor",
  "observations": [],
  "warnings": []
}

Never invent unreadable prices.
Never claim certainty or guaranteed profit.
Never create an exact entry/stop/target from visual pixels when the value cannot be reliably read.
The deterministic risk engine remains the final gate.
