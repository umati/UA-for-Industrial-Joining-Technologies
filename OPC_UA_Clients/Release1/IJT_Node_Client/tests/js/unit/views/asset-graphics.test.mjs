import { describe, it, expect, vi, beforeEach } from 'vitest'
import AssetGraphics from '../../../../javascripts/views/assets/asset-graphics.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAssetManager (resolveWith) {
  return {
    setupAndLoadAllAssets: vi.fn(() => Promise.resolve(resolveWith))
  }
}

function makeNode (nodeId, displayName = 'Node') {
  const node = {
    nodeId,
    displayName,
    assetGraphicData: null,
    _relations: {}
  }
  node.getRelations = (type) => node._relations[type] || []
  return node
}

function makeEmptyAssetObject () {
  return {
    Controllers: [],
    Tools: [],
    PowerSupplies: [],
    Feeders: [],
    Cables: [],
    Accessories: [],
    Servos: [],
    MemoryDevices: [],
    SubComponents: [],
    Batteries: [],
    Sensors: []
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AssetGraphics', () => {
  let am, ag

  beforeEach(() => {
    am = makeAssetManager(makeEmptyAssetObject())
    ag = new AssetGraphics(am)
  })

  // ── Constructor ──────────────────────────────────────────────────────────────

  describe('constructor', () => {
    it('title is "Assets" (inherited from BasicScreen)', () => {
      expect(ag.title).toBe('Assets')
    })

    it('stores the assetManager', () => {
      expect(ag.assetManager).toBe(am)
    })

    it('creates a container div with class draw-asset-box', () => {
      expect(ag.container.tagName).toBe('DIV')
      expect(ag.container.classList.contains('draw-asset-box')).toBe(true)
    })

    it('appends the container to backGround', () => {
      expect(ag.backGround.contains(ag.container)).toBe(true)
    })
  })

  // ── initiate ─────────────────────────────────────────────────────────────────

  describe('initiate()', () => {
    it('calls setupAndLoadAllAssets on the assetManager', async () => {
      await ag.initiate()
      expect(am.setupAndLoadAllAssets).toHaveBeenCalledOnce()
    })

    it('calls draw() with the resolved asset object', async () => {
      const assetObject = makeEmptyAssetObject()
      am = makeAssetManager(assetObject)
      ag = new AssetGraphics(am)
      const drawSpy = vi.spyOn(ag, 'draw')
      await ag.initiate()
      // Wait for microtask queue to flush
      await Promise.resolve()
      expect(drawSpy).toHaveBeenCalledWith(assetObject)
    })
  })

  // ── draw() ────────────────────────────────────────────────────────────────────

  describe('draw()', () => {
    it('does nothing when Controllers is empty', () => {
      const assetObject = makeEmptyAssetObject()
      expect(() => ag.draw(assetObject)).not.toThrow()
    })

    it('calls createController for each controller', () => {
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      const assetObject = { ...makeEmptyAssetObject(), Controllers: [ctrl] }
      const spy = vi.spyOn(ag, 'createController')
      ag.draw(assetObject)
      expect(spy).toHaveBeenCalledWith(ctrl, 0, 1)
    })

    it('passes controller index and total count to createController', () => {
      const ctrl1 = makeNode('ctrl-1', 'Controller 1')
      const ctrl2 = makeNode('ctrl-2', 'Controller 2')
      const assetObject = { ...makeEmptyAssetObject(), Controllers: [ctrl1, ctrl2] }
      const spy = vi.spyOn(ag, 'createController')
      ag.draw(assetObject)
      expect(spy).toHaveBeenCalledWith(ctrl1, 0, 2)
      expect(spy).toHaveBeenCalledWith(ctrl2, 1, 2)
    })

    it('calls createTool when a tool nodeId matches a controller association', () => {
      const tool = makeNode('tool-1', 'Tool 1')
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl._relations.association = [{ nodeId: 'tool-1' }]
      const assetObject = { ...makeEmptyAssetObject(), Controllers: [ctrl], Tools: [tool] }
      const spy = vi.spyOn(ag, 'createTool')
      ag.draw(assetObject)
      expect(spy).toHaveBeenCalledWith(tool, ctrl)
    })

    it('does not call createTool when tool nodeId does not match any association', () => {
      const tool = makeNode('tool-99', 'Tool 99')
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl._relations.association = [{ nodeId: 'other-id' }]
      const assetObject = { ...makeEmptyAssetObject(), Controllers: [ctrl], Tools: [tool] }
      const spy = vi.spyOn(ag, 'createTool')
      ag.draw(assetObject)
      expect(spy).not.toHaveBeenCalled()
    })

    it('calls addExternal when an external nodeId matches a controller association', () => {
      const ps = makeNode('ps-1', 'PowerSupply 1')
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl._relations.association = [{ nodeId: 'ps-1' }]
      const assetObject = { ...makeEmptyAssetObject(), Controllers: [ctrl], PowerSupplies: [ps] }
      const spy = vi.spyOn(ag, 'addExternal')
      ag.draw(assetObject)
      expect(spy).toHaveBeenCalledWith(ps, ctrl)
    })

    it('calls addInternal when an internal nodeId matches a controller association', () => {
      const servo = makeNode('servo-1', 'Servo 1')
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl._relations.association = [{ nodeId: 'servo-1' }]
      const assetObject = { ...makeEmptyAssetObject(), Controllers: [ctrl], Servos: [servo] }
      const spy = vi.spyOn(ag, 'addInternal')
      ag.draw(assetObject)
      expect(spy).toHaveBeenCalledWith(servo, ctrl)
    })

    it('recursively calls createTool for tools associated with a tool', () => {
      const innerTool = makeNode('tool-inner', 'Inner Tool')
      const outerTool = makeNode('tool-outer', 'Outer Tool')
      outerTool._relations.association = [{ nodeId: 'tool-inner' }]
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl._relations.association = [{ nodeId: 'tool-outer' }]
      const assetObject = {
        ...makeEmptyAssetObject(),
        Controllers: [ctrl],
        Tools: [outerTool, innerTool]
      }
      // addVertical is called from createTool, which calls createAssetContainer
      // Just ensure no throw — deep recursion is exercised
      expect(() => ag.draw(assetObject)).not.toThrow()
    })

    it('handles all external categories (Feeders, Cables, Accessories)', () => {
      const feeder = makeNode('feeder-1', 'Feeder 1')
      const cable = makeNode('cable-1', 'Cable 1')
      const acc = makeNode('acc-1', 'Acc 1')
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl._relations.association = [{ nodeId: 'feeder-1' }, { nodeId: 'cable-1' }, { nodeId: 'acc-1' }]
      const assetObject = {
        ...makeEmptyAssetObject(),
        Controllers: [ctrl],
        Feeders: [feeder],
        Cables: [cable],
        Accessories: [acc]
      }
      const spy = vi.spyOn(ag, 'addExternal')
      ag.draw(assetObject)
      expect(spy).toHaveBeenCalledTimes(3)
    })

    it('handles all internal categories (MemoryDevices, SubComponents, Batteries, Sensors)', () => {
      const mem = makeNode('mem-1', 'Mem 1')
      const sub = makeNode('sub-1', 'Sub 1')
      const bat = makeNode('bat-1', 'Bat 1')
      const sen = makeNode('sen-1', 'Sen 1')
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl._relations.association = [
        { nodeId: 'mem-1' }, { nodeId: 'sub-1' }, { nodeId: 'bat-1' }, { nodeId: 'sen-1' }
      ]
      const assetObject = {
        ...makeEmptyAssetObject(),
        Controllers: [ctrl],
        MemoryDevices: [mem],
        SubComponents: [sub],
        Batteries: [bat],
        Sensors: [sen]
      }
      const spy = vi.spyOn(ag, 'addInternal')
      ag.draw(assetObject)
      expect(spy).toHaveBeenCalledTimes(4)
    })
  })

  // ── createController ──────────────────────────────────────────────────────────

  describe('createController()', () => {
    it('appends a mainbox div to container', () => {
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ag.createController(ctrl, 0, 1)
      expect(ag.container.children.length).toBe(1)
    })

    it('mainbox has class asset-area', () => {
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ag.createController(ctrl, 0, 1)
      expect(ag.container.children[0].classList.contains('asset-area')).toBe(true)
    })

    it('initialises assetGraphicData on the node when absent', () => {
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl.assetGraphicData = null
      ag.createController(ctrl, 0, 1)
      expect(ctrl.assetGraphicData).not.toBeNull()
    })

    it('sets tools property on assetGraphicData', () => {
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ag.createController(ctrl, 0, 1)
      expect(ctrl.assetGraphicData.tools).toBeDefined()
    })

    it('sets correct top % based on controller index', () => {
      const ctrl1 = makeNode('ctrl-1')
      const ctrl2 = makeNode('ctrl-2')
      ag.createController(ctrl1, 0, 2)
      ag.createController(ctrl2, 1, 2)
      const boxes = ag.container.children
      expect(boxes[0].style.top).toBe('0%')
      expect(boxes[1].style.top).toBe('50%')
    })

    it('does not reinitialise assetGraphicData when already defined', () => {
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      ctrl.assetGraphicData = { existingProp: true }
      ag.createController(ctrl, 0, 1)
      // The false branch — existing data is preserved
      expect(ctrl.assetGraphicData.existingProp).toBe(true)
    })

    it('returns the asset div from createAssetContainer', () => {
      const ctrl = makeNode('ctrl-1', 'Controller 1')
      const result = ag.createController(ctrl, 0, 1)
      expect(result.tagName).toBe('DIV')
    })
  })

  // ── addInternal / addExternal / createTool ────────────────────────────────────

  describe('addInternal()', () => {
    it('delegates to addHorizontal with assetGraphicData.internals', () => {
      const container = document.createElement('div')
      const internalsEl = document.createElement('div')
      internalsEl.assetInternals = []
      const node = makeNode('n1', 'Node1')
      const containerNode = { assetGraphicData: { internals: internalsEl } }
      const spy = vi.spyOn(ag, 'addHorizontal')
      ag.addInternal(node, containerNode)
      expect(spy).toHaveBeenCalledWith(node, internalsEl)
    })
  })

  describe('addExternal()', () => {
    it('delegates to addHorizontal with assetGraphicData.externals', () => {
      const externalsEl = document.createElement('div')
      externalsEl.assetInternals = []
      const node = makeNode('n1', 'Node1')
      const containerNode = { assetGraphicData: { externals: externalsEl } }
      const spy = vi.spyOn(ag, 'addHorizontal')
      ag.addExternal(node, containerNode)
      expect(spy).toHaveBeenCalledWith(node, externalsEl)
    })
  })

  describe('createTool()', () => {
    it('delegates to addVertical with assetGraphicData.tools', () => {
      const toolsEl = document.createElement('div')
      toolsEl.assetInternals = []
      const node = makeNode('n1', 'Tool1')
      const containerNode = { assetGraphicData: { tools: toolsEl } }
      const spy = vi.spyOn(ag, 'addVertical')
      ag.createTool(node, containerNode)
      expect(spy).toHaveBeenCalledWith(node, toolsEl)
    })
  })

  // ── createAssetContainer ──────────────────────────────────────────────────────

  describe('createAssetContainer()', () => {
    it('appends two children to the container', () => {
      const node = makeNode('n1', 'MyNode')
      const container = document.createElement('div')
      ag.createAssetContainer(node, container)
      expect(container.children.length).toBe(2)
    })

    it('first child (asset) has class asset-area', () => {
      const node = makeNode('n1', 'MyNode')
      const container = document.createElement('div')
      ag.createAssetContainer(node, container)
      expect(container.children[0].classList.contains('asset-area')).toBe(true)
    })

    it('asset div innerText is the node displayName', () => {
      const node = makeNode('n1', 'MyName')
      const container = document.createElement('div')
      ag.createAssetContainer(node, container)
      expect(container.children[0].innerText).toBe('MyName')
    })

    it('initialises assetGraphicData when null', () => {
      const node = makeNode('n1', 'X')
      node.assetGraphicData = null
      const container = document.createElement('div')
      ag.createAssetContainer(node, container)
      expect(node.assetGraphicData).not.toBeNull()
    })

    it('sets assetGraphicData.internals and assetGraphicData.externals', () => {
      const node = makeNode('n1', 'X')
      const container = document.createElement('div')
      ag.createAssetContainer(node, container)
      expect(node.assetGraphicData.internals).toBeDefined()
      expect(node.assetGraphicData.externals).toBeDefined()
    })

    it('returns the asset div', () => {
      const node = makeNode('n1', 'X')
      const container = document.createElement('div')
      const result = ag.createAssetContainer(node, container)
      expect(result.tagName).toBe('DIV')
      expect(result.classList.contains('asset-area')).toBe(true)
    })
  })

  // ── addHorizontal ─────────────────────────────────────────────────────────────

  describe('addHorizontal()', () => {
    function makeContainer () {
      const el = document.createElement('div')
      el.assetInternals = []
      return el
    }

    it('appends a child with class asset-box to the container', () => {
      const node = makeNode('n1', 'Node1')
      const container = makeContainer()
      ag.addHorizontal(node, container)
      expect(container.children.length).toBe(1)
      expect(container.children[0].classList.contains('asset-box')).toBe(true)
    })

    it('sets innerText to node displayName', () => {
      const node = makeNode('n1', 'MyLabel')
      const container = makeContainer()
      ag.addHorizontal(node, container)
      expect(container.children[0].innerText).toBe('MyLabel')
    })

    it('pushes the box into container.assetInternals', () => {
      const node = makeNode('n1', 'N')
      const container = makeContainer()
      ag.addHorizontal(node, container)
      expect(container.assetInternals).toHaveLength(1)
    })

    it('returns the created mainbox', () => {
      const node = makeNode('n1', 'N')
      const container = makeContainer()
      const result = ag.addHorizontal(node, container)
      expect(result.tagName).toBe('DIV')
    })

    it('recalculates widths when a second item is added', () => {
      const n1 = makeNode('n1', 'N1')
      const n2 = makeNode('n2', 'N2')
      const container = makeContainer()
      const box1 = ag.addHorizontal(n1, container)
      const box2 = ag.addHorizontal(n2, container)
      // With 2 items: width = 50, left0 = 5%, left1 = 55%
      expect(box1.style.left).toBe('5%')
      expect(box2.style.left).toBe('55%')
      expect(box1.style.width).toBe('40%')
    })
  })

  // ── addVertical ───────────────────────────────────────────────────────────────

  describe('addVertical()', () => {
    function makeContainer () {
      const el = document.createElement('div')
      el.assetInternals = []
      return el
    }

    it('appends a child with class asset-box to the container', () => {
      const node = makeNode('n1', 'ToolNode')
      const container = makeContainer()
      ag.addVertical(node, container)
      expect(container.children.length).toBe(1)
      expect(container.children[0].classList.contains('asset-box')).toBe(true)
    })

    it('pushes the box into container.assetInternals', () => {
      const node = makeNode('n1', 'T')
      const container = makeContainer()
      ag.addVertical(node, container)
      expect(container.assetInternals).toHaveLength(1)
    })

    it('calls createAssetContainer on the new box', () => {
      const node = makeNode('n1', 'T')
      const container = makeContainer()
      const spy = vi.spyOn(ag, 'createAssetContainer')
      ag.addVertical(node, container)
      expect(spy).toHaveBeenCalledOnce()
    })

    it('returns the created mainbox', () => {
      const node = makeNode('n1', 'T')
      const container = makeContainer()
      const result = ag.addVertical(node, container)
      expect(result.tagName).toBe('DIV')
    })

    it('recalculates heights when a second item is added', () => {
      const n1 = makeNode('n1', 'T1')
      const n2 = makeNode('n2', 'T2')
      const container = makeContainer()
      const box1 = ag.addVertical(n1, container)
      const box2 = ag.addVertical(n2, container)
      // With 2 items: height = 50, top0 = 5%, top1 = 55%
      expect(box1.style.top).toBe('5%')
      expect(box2.style.top).toBe('55%')
      expect(box1.style.height).toBe('40%')
    })
  })
})
