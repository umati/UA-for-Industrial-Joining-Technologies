export function toolsFromProductInstanceUriResponse (response) {
  const tools = response?.message?.tools || response?.tools
  if (!Array.isArray(tools)) return []

  return tools.map(tool => ({
    ...tool,
    productInstanceUri: String(tool?.productInstanceUri || tool?.productinstanceuri || '').trim()
  }))
}

export function firstProductInstanceUri (response) {
  return toolsFromProductInstanceUriResponse(response)
    .map(tool => tool.productInstanceUri)
    .find(Boolean) || ''
}
