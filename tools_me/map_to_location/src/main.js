import './style.css'

const MAX_X = 27
const MAX_Y = 13
const SCALE = 28
const MARGIN = { top: 36, right: 54, bottom: 62, left: 54 }
const SVG_WIDTH = MARGIN.left + MARGIN.right + MAX_X * SCALE
const SVG_HEIGHT = MARGIN.top + MARGIN.bottom + MAX_Y * SCALE
const POLYGON_VERTICES = [
  [0, 13],
  [13, 0],
  [14, 0],
  [27, 13],
]

const validPoints = []
for (let y = 0; y <= MAX_Y; y += 1) {
  for (let x = 13 - y; x <= 14 + y; x += 1) {
    validPoints.push({ x, y, key: `${x},${y}` })
  }
}

const pointToSvg = (x, y) => ({
  cx: MARGIN.left + x * SCALE,
  cy: MARGIN.top + (MAX_Y - y) * SCALE,
})

const formatPoints = (points) =>
  points.map(({ x, y }) => `(${x},${y})`).join(',')

const dedupePoints = (points) => {
  const seen = new Set()
  return points.filter((point) => {
    if (seen.has(point.key)) {
      return false
    }

    seen.add(point.key)
    return true
  })
}

const parseInput = (text) => {
  const trimmed = text.trim()
  if (!trimmed) {
    return { ok: true, points: [] }
  }

  const matches = [...trimmed.matchAll(/\(\s*(\d+)\s*,\s*(\d+)\s*\)/g)]
  const leftover = trimmed
    .replace(/\(\s*\d+\s*,\s*\d+\s*\)/g, '')
    .replace(/[\s,，;；]+/g, '')

  if (matches.length === 0 || leftover.length > 0) {
    return {
      ok: false,
      error: '请输入形如 (13,0),(14,0),(15,1) 的坐标列表。',
    }
  }

  const parsed = []
  for (const match of matches) {
    const x = Number(match[1])
    const y = Number(match[2])
    const isInside = y >= 0 && y <= MAX_Y && x >= 13 - y && x <= 14 + y

    if (!isInside) {
      return {
        ok: false,
        error: `坐标 (${x},${y}) 不在梯形范围内。`,
      }
    }

    parsed.push({ x, y, key: `${x},${y}` })
  }

  return { ok: true, points: dedupePoints(parsed) }
}

const polygonPoints = POLYGON_VERTICES.map(([x, y]) => {
  const { cx, cy } = pointToSvg(x, y)
  return `${cx},${cy}`
}).join(' ')

const pointMarkup = validPoints
  .map(({ x, y, key }) => {
    const { cx, cy } = pointToSvg(x, y)

    return `
      <g class="map-point" data-key="${key}">
        <circle class="point-hit" data-key="${key}" cx="${cx}" cy="${cy}" r="13"></circle>
        <circle class="point-dot" cx="${cx}" cy="${cy}" r="4.2"></circle>
      </g>
    `
  })
  .join('')

document.querySelector('#app').innerHTML = `
  <main class="layout">
    <section class="panel map-panel">
      <div class="panel-header">
        <div>
          <p class="eyebrow">Map</p>
          <h1>坐标点选器</h1>
        </div>
        <button type="button" id="clearSelection">清空当前点位</button>
      </div>
      <p class="panel-copy">
        左侧可直接点选梯形内的离散坐标点；再次点击同一点会取消。坐标规则为
        <code>(x1,x2)</code>，其中 <code>x1</code> 横向向右增大，<code>x2</code> 纵向向上增大。
      </p>
      <div class="map-shell">
        <svg
          class="map-svg"
          viewBox="0 0 ${SVG_WIDTH} ${SVG_HEIGHT}"
          aria-label="可点击的梯形地图"
          role="img"
        >
          <polygon class="map-shape" points="${polygonPoints}"></polygon>
          <g class="axis-labels">
            <text x="${pointToSvg(0, 13).cx}" y="${pointToSvg(0, 13).cy - 14}">(0,13)</text>
            <text x="${pointToSvg(13, 0).cx - 20}" y="${pointToSvg(13, 0).cy + 28}">(13,0)</text>
            <text x="${pointToSvg(14, 0).cx + 8}" y="${pointToSvg(14, 0).cy + 28}">(14,0)</text>
            <text x="${pointToSvg(27, 13).cx - 46}" y="${pointToSvg(27, 13).cy - 14}">(27,13)</text>
          </g>
          ${pointMarkup}
        </svg>
      </div>
    </section>

    <section class="panel side-panel">
      <div class="io-block">
        <label for="inputBox">Input</label>
        <textarea
          id="inputBox"
          spellcheck="false"
          placeholder="例如: (13,0),(14,0),(15,1)"
        ></textarea>
        <div class="button-row">
          <button type="button" id="applyInput">应用到地图</button>
          <button type="button" id="copyOutput">复制 output</button>
        </div>
        <p id="feedback" class="feedback">支持输入多个坐标，重复坐标会自动去重。</p>
      </div>

      <div class="io-block">
        <label for="outputBox">Output</label>
        <textarea
          id="outputBox"
          readonly
          spellcheck="false"
          placeholder="点击左侧地图后，这里会显示坐标结果"
        ></textarea>
      </div>
    </section>
  </main>
`

const inputBox = document.querySelector('#inputBox')
const outputBox = document.querySelector('#outputBox')
const feedback = document.querySelector('#feedback')
const clearSelectionButton = document.querySelector('#clearSelection')
const applyInputButton = document.querySelector('#applyInput')
const copyOutputButton = document.querySelector('#copyOutput')
const pointGroups = [...document.querySelectorAll('.map-point')]
const mapSvg = document.querySelector('.map-svg')
const mapShell = document.querySelector('.map-shell')

let selectedPoints = []
const debugRunId = `run-${Date.now()}`

const collectGeometry = (key) => {
  const group = document.querySelector(`.map-point[data-key="${key}"]`)
  if (!group) {
    return null
  }

  const hit = group.querySelector('.point-hit')
  const dot = group.querySelector('.point-dot')
  const groupRect = group.getBoundingClientRect()
  const hitRect = hit.getBoundingClientRect()
  const dotRect = dot.getBoundingClientRect()
  const dotStyle = window.getComputedStyle(dot)

  return {
    key,
    groupSelected: group.classList.contains('selected'),
    cx: Number(dot.getAttribute('cx')),
    cy: Number(dot.getAttribute('cy')),
    dotTransform: dotStyle.transform,
    dotTransformOrigin: dotStyle.transformOrigin,
    groupRect: {
      left: Math.round(groupRect.left * 100) / 100,
      top: Math.round(groupRect.top * 100) / 100,
      width: Math.round(groupRect.width * 100) / 100,
      height: Math.round(groupRect.height * 100) / 100,
    },
    hitRect: {
      left: Math.round(hitRect.left * 100) / 100,
      top: Math.round(hitRect.top * 100) / 100,
      width: Math.round(hitRect.width * 100) / 100,
      height: Math.round(hitRect.height * 100) / 100,
    },
    dotRect: {
      left: Math.round(dotRect.left * 100) / 100,
      top: Math.round(dotRect.top * 100) / 100,
      width: Math.round(dotRect.width * 100) / 100,
      height: Math.round(dotRect.height * 100) / 100,
    },
  }
}

const postDebugLog = (hypothesisId, location, message, data) => {
  fetch('http://127.0.0.1:7818/ingest/9d764385-5e87-481e-97f5-386e1a6f19ee', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Debug-Session-Id': 'f9afbb',
    },
    body: JSON.stringify({
      sessionId: 'f9afbb',
      runId: debugRunId,
      hypothesisId,
      location,
      message,
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {})
}

const setFeedback = (message, type = 'info') => {
  feedback.textContent = message
  feedback.dataset.type = type
}

const render = () => {
  const selectedKeys = new Set(selectedPoints.map((point) => point.key))
  pointGroups.forEach((group) => {
    group.classList.toggle('selected', selectedKeys.has(group.dataset.key))
  })
  outputBox.value = formatPoints(selectedPoints)

  // #region agent log
  postDebugLog('H1,H2,H3,H4', 'src/main.js:render', 'render snapshot', {
    selectedKeys: [...selectedKeys],
    selectedGeometry: selectedPoints.slice(0, 4).map((point) => collectGeometry(point.key)),
    anchorGeometry: ['13,0', '14,0', '0,13', '27,13'].map((key) => collectGeometry(key)),
    svgRect: mapSvg
      ? {
          left: Math.round(mapSvg.getBoundingClientRect().left * 100) / 100,
          top: Math.round(mapSvg.getBoundingClientRect().top * 100) / 100,
          width: Math.round(mapSvg.getBoundingClientRect().width * 100) / 100,
          height: Math.round(mapSvg.getBoundingClientRect().height * 100) / 100,
        }
      : null,
  })
  // #endregion
}

const replacePoints = (points) => {
  selectedPoints = [...points]
  render()
}

const togglePoint = (key) => {
  const index = selectedPoints.findIndex((point) => point.key === key)

  if (index >= 0) {
    selectedPoints.splice(index, 1)
  } else {
    const point = validPoints.find((item) => item.key === key)
    if (!point) {
      return
    }
    selectedPoints.push(point)
  }

  render()
  setFeedback(`当前已选择 ${selectedPoints.length} 个点。`)

  // #region agent log
  postDebugLog('H2,H4', 'src/main.js:togglePoint', 'toggle point completed', {
    toggledKey: key,
    selectedKeysAfterToggle: selectedPoints.map((point) => point.key),
    toggledGeometryAfterToggle: collectGeometry(key),
  })
  // #endregion
}

document.querySelector('.map-svg').addEventListener('click', (event) => {
  const target = event.target.closest('[data-key]')
  if (!target) {
    return
  }

  // #region agent log
  postDebugLog('H4', 'src/main.js:mapClick', 'map click received', {
    targetKey: target.dataset.key,
    targetTagName: event.target.tagName,
    clientX: Math.round(event.clientX * 100) / 100,
    clientY: Math.round(event.clientY * 100) / 100,
    geometryBeforeToggle: collectGeometry(target.dataset.key),
  })
  // #endregion

  togglePoint(target.dataset.key)
})

applyInputButton.addEventListener('click', () => {
  const result = parseInput(inputBox.value)

  if (!result.ok) {
    setFeedback(result.error, 'error')
    return
  }

  replacePoints(result.points)
  inputBox.value = formatPoints(result.points)
  setFeedback(`已从 input 同步 ${result.points.length} 个点到地图。`, 'success')
})

clearSelectionButton.addEventListener('click', () => {
  replacePoints([])
  setFeedback('已清空当前点位。', 'success')
})

copyOutputButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(outputBox.value)
    setFeedback('output 已复制到剪贴板。', 'success')
  } catch {
    setFeedback('复制失败，请手动复制 output 内容。', 'error')
  }
})

render()

// #region agent log
postDebugLog('H1,H2,H3', 'src/main.js:init', 'initial layout snapshot', {
  svgViewBox: mapSvg?.getAttribute('viewBox') ?? null,
  shellRect: mapShell
    ? {
        left: Math.round(mapShell.getBoundingClientRect().left * 100) / 100,
        top: Math.round(mapShell.getBoundingClientRect().top * 100) / 100,
        width: Math.round(mapShell.getBoundingClientRect().width * 100) / 100,
        height: Math.round(mapShell.getBoundingClientRect().height * 100) / 100,
      }
    : null,
  svgRect: mapSvg
    ? {
        left: Math.round(mapSvg.getBoundingClientRect().left * 100) / 100,
        top: Math.round(mapSvg.getBoundingClientRect().top * 100) / 100,
        width: Math.round(mapSvg.getBoundingClientRect().width * 100) / 100,
        height: Math.round(mapSvg.getBoundingClientRect().height * 100) / 100,
      }
    : null,
  sampleGeometry: ['13,0', '14,0', '0,13', '27,13'].map((key) => collectGeometry(key)),
})
// #endregion
