import { describe, expect, it } from 'vitest'
import {
  joiningProcessIdFromEntry,
  joiningProcessOriginIdFromEntry,
  joiningProcessSelectionNameFromEntry
} from '../../../src/javascripts/ijt-support/methods/method-discovery-cache.mjs'

describe('joining-process discovery normalization', () => {
  it('reads direct and wrapped joining-process identities', () => {
    expect(joiningProcessIdFromEntry({ JoiningProcessId: ' Process-1 ' })).toBe('Process-1')
    expect(joiningProcessIdFromEntry({ Value: { Id: ' Process-2 ' } })).toBe('Process-2')
    expect(joiningProcessIdFromEntry({ ProgramId: 3 })).toBe('3')
  })

  it('falls back to nested metadata and plain string identifiers', () => {
    const metadata = {
      JoiningProcessMetaData: {
        JoiningProcessId: ' Process-4 ',
        JoiningProcessOriginId: ' Origin-4 ',
        SelectionName: ' Program 4 '
      }
    }

    expect(joiningProcessIdFromEntry(metadata)).toBe('Process-4')
    expect(joiningProcessOriginIdFromEntry(metadata)).toBe('Origin-4')
    expect(joiningProcessSelectionNameFromEntry(metadata)).toBe('Program 4')
    expect(joiningProcessIdFromEntry(' Process-5 ')).toBe('Process-5')
  })

  it('normalizes direct origin and selection-name aliases', () => {
    expect(joiningProcessOriginIdFromEntry({ JoiningProcessOriginId: 7 })).toBe('7')
    expect(joiningProcessSelectionNameFromEntry({ SelectionName: ' Program 7 ' })).toBe('Program 7')
    expect(joiningProcessSelectionNameFromEntry({ Name: ' Program 8 ' })).toBe('Program 8')
  })

  it('returns empty values for missing discovery fields', () => {
    expect(joiningProcessIdFromEntry(null)).toBe('')
    expect(joiningProcessOriginIdFromEntry({})).toBe('')
    expect(joiningProcessSelectionNameFromEntry({ Value: null })).toBe('')
  })
})
