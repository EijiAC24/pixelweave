local input = app.params["input"]
local output = app.params["output"]
local frame_width = tonumber(app.params["frame_width"])
local frame_height = tonumber(app.params["frame_height"])
local columns = tonumber(app.params["columns"])
local duration_ms = tonumber(app.params["frame_duration_ms"] or "100")

assert(input, "missing --script-param input")
assert(output, "missing --script-param output")
assert(frame_width and frame_width > 0, "missing or invalid frame_width")
assert(frame_height and frame_height > 0, "missing or invalid frame_height")
assert(columns and columns > 0, "missing or invalid columns")
assert(duration_ms and duration_ms > 0, "missing or invalid frame_duration_ms")

local source = app.open(input)
assert(source, "could not open sprite sheet: " .. input)

local imported = app.command.ImportSpriteSheet {
  ui = false,
  type = SpriteSheetType.ROWS,
  frameBounds = Rectangle(0, 0, frame_width, frame_height),
  padding = Size(0, 0),
  partialTiles = false,
}
assert(imported, "Aseprite Import Sprite Sheet failed")

local sprite = app.activeSprite
assert(sprite, "no imported sprite is active")
assert(#sprite.frames == columns, "imported frame count does not match columns")

for _, frame in ipairs(sprite.frames) do
  frame.duration = duration_ms / 1000
end

sprite:saveAs(output)
print(string.format(
  "saved=%s frames=%d size=%dx%d duration_ms=%d",
  output,
  #sprite.frames,
  sprite.width,
  sprite.height,
  duration_ms
))
