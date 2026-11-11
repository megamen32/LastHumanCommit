import { expect, test } from "bun:test"
import { bossSpokenText } from "../plugins/last-human-commit/opencode/lhc-boss-v2"

test("Boss words pass through verbatim, including paragraphs and long responses", () => {
  const first = "Слушай, у нас до сих пор не работает запуск.\\nПоправь адаптер."
  const second = "Вот конкретный путь:\\n1. Исправь вызов.\\n2. Проверь в приложении."
  const long = "Длинное объяснение: " + "работает не то. ".repeat(500)
  const messages = [
    { info: {role:"user"}, parts: [{type:"text",text:"Context"}] },
    { info: {role:"assistant"}, parts: [{type:"text",text:first}, {type:"tool",tool:"read",state:{output:"private"}}] },
    { info: {role:"assistant"}, parts: [{type:"text",text:second}] },
    { info: {role:"assistant"}, parts: [{type:"text",text:long}] }
  ]
  expect(bossSpokenText(messages)).toBe([first,second,long].join("\n\n"))
})
