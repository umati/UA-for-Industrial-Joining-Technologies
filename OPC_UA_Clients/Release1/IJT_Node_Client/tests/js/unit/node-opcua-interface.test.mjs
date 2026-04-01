import { describe, it, expect } from 'vitest'
import { isValidEndpointUrl, ENDPOINT_URL_PATTERN } from '../../../javascripts/ijt-support/client/node-opcua-interface.mjs'

describe('isValidEndpointUrl (SSRF guard)', () => {
  it('accepts a well-formed opc.tcp URL with port', () => {
    expect(isValidEndpointUrl('opc.tcp://localhost:40451')).toBe(true)
  })

  it('accepts hostname with port', () => {
    expect(isValidEndpointUrl('opc.tcp://my-server.example.com:4840')).toBe(true)
  })

  it('accepts URL with path segment', () => {
    expect(isValidEndpointUrl('opc.tcp://server:4840/UA/Server')).toBe(true)
  })

  it('rejects null', () => {
    expect(isValidEndpointUrl(null)).toBe(false)
  })

  it('rejects undefined', () => {
    expect(isValidEndpointUrl(undefined)).toBe(false)
  })

  it('rejects empty string', () => {
    expect(isValidEndpointUrl('')).toBe(false)
  })

  it('rejects non-opc.tcp scheme (http)', () => {
    expect(isValidEndpointUrl('http://server:4840')).toBe(false)
  })

  it('rejects path traversal suffix attempt', () => {
    expect(isValidEndpointUrl('opc.tcp://server:4840/../../etc/passwd')).toBe(false)
  })

  it('rejects URL with spaces', () => {
    expect(isValidEndpointUrl('opc.tcp://server name:4840')).toBe(false)
  })

  it('rejects number input', () => {
    expect(isValidEndpointUrl(12345)).toBe(false)
  })

  it('rejects URL with javascript: injection', () => {
    expect(isValidEndpointUrl('javascript:alert(1)')).toBe(false)
  })

  it('ENDPOINT_URL_PATTERN is a RegExp', () => {
    expect(ENDPOINT_URL_PATTERN).toBeInstanceOf(RegExp)
  })
})
