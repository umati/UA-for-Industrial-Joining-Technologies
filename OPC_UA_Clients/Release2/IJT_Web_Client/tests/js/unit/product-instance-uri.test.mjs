import { describe, expect, it } from 'vitest'
import {
  firstProductInstanceUri,
  toolsFromProductInstanceUriResponse
} from '../../../src/javascripts/ijt-support/tools/product-instance-uri.mjs'

describe('ProductInstanceUri response helpers', () => {
  it('uses the first non-empty Tool URI from the socket response', () => {
    const response = {
      message: {
        tools: [
          { toolName: 'Tool_1', productInstanceUri: '' },
          { toolName: 'Tool_2', productInstanceUri: ' urn:tool:2 ' }
        ]
      }
    }

    expect(firstProductInstanceUri(response)).toBe('urn:tool:2')
  })

  it('normalizes lower-case server fields without discarding tool data', () => {
    const tools = toolsFromProductInstanceUriResponse({
      tools: [{ toolName: 'Tool_1', productinstanceuri: 'urn:tool:1', path: 'Tools/Tool_1' }]
    })

    expect(tools).toEqual([
      { toolName: 'Tool_1', productinstanceuri: 'urn:tool:1', productInstanceUri: 'urn:tool:1', path: 'Tools/Tool_1' }
    ])
  })
})
