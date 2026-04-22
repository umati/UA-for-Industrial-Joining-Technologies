import { describe, expect, it, vi } from 'vitest'
import { deleteCurrentFilter, ensureAllFiltersExist, selectFilter } from '../../../src/javascripts/views/envelope/ui/filter/assignment-state.mjs'
import { FilterAll, FilterNever, FilterTool } from '../../../src/javascripts/views/envelope/core/filter/filter-models.mjs'

function makeScreen () {
  return {
    currentFilter: null,
    filterArea: { innerHTML: 'occupied' },
    filterView: { draw: vi.fn() },
    refreshFilterList: vi.fn(),
    refreshFilterOptionsForLimits: vi.fn()
  }
}

describe('selectFilter', () => {
  it('does not draw details for Always filter', () => {
    const screen = makeScreen()
    const filter = new FilterAll()

    selectFilter(screen, filter)

    expect(screen.filterView.draw).not.toHaveBeenCalled()
    expect(screen.filterArea.innerHTML).toBe('')
  })

  it('does not draw details for Never filter', () => {
    const screen = makeScreen()
    const filter = new FilterNever()

    selectFilter(screen, filter)

    expect(screen.filterView.draw).not.toHaveBeenCalled()
    expect(screen.filterArea.innerHTML).toBe('')
  })

  it('draws details for non-exclusive filters', () => {
    const screen = makeScreen()
    const filter = new FilterTool('Tool1')

    selectFilter(screen, filter)

    expect(screen.filterView.draw).toHaveBeenCalledWith(filter)
  })
})

function makeStateScreen () {
  return {
    filterIdCounter: 1,
    filters: [],
    currentFilter: null,
    limits: [],
    refreshFilterList: vi.fn(),
    refreshFilterOptionsForLimits: vi.fn(),
    selectFilter: vi.fn()
  }
}

describe('exclusive filters availability', () => {
  it('ensureAllFiltersExist guarantees both Always and Never filters', () => {
    const screen = makeStateScreen()

    ensureAllFiltersExist(screen)

    const types = screen.filters.map((filter) => filter.constructor.name)
    expect(types).toContain('FilterAll')
    expect(types).toContain('FilterNever')
  })

  it('deleteCurrentFilter recreates Never when it is deleted', () => {
    const screen = makeStateScreen()
    const always = new FilterAll()
    always.__id = 'fil-1'
    const never = new FilterNever()
    never.__id = 'fil-2'
    const tool = new FilterTool('Tool1')
    tool.__id = 'fil-3'
    screen.filters = [always, never, tool]
    screen.filterIdCounter = 4
    screen.currentFilter = never

    deleteCurrentFilter(screen)

    const types = screen.filters.map((filter) => filter.constructor.name)
    expect(types).toContain('FilterAll')
    expect(types).toContain('FilterNever')
  })

  it('deleteCurrentFilter does not delete Always or Never', () => {
    const screen = makeStateScreen()
    const always = new FilterAll()
    always.__id = 'fil-1'
    const never = new FilterNever()
    never.__id = 'fil-2'
    const tool = new FilterTool('Tool1')
    tool.__id = 'fil-3'
    screen.filters = [always, never, tool]
    screen.filterIdCounter = 4
    screen.currentFilter = always

    deleteCurrentFilter(screen)
    expect(screen.filters.map((filter) => filter.__id)).toEqual(['fil-1', 'fil-2', 'fil-3'])

    screen.currentFilter = never
    deleteCurrentFilter(screen)
    expect(screen.filters.map((filter) => filter.__id)).toEqual(['fil-1', 'fil-2', 'fil-3'])
  })
})
