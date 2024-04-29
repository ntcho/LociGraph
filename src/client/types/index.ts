import type { ResponseBody as WebpageData } from '~contents/get-webpage-data';

export type Relation = {
    // see dtos.py:Relation
    entity: string
    attribute: string
    value: string
}

export type RelationQuery = {
    // see dtos.py:RelationQuery
    entity: string
    attribute?: string
    value?: string
}

export type ActionElement = {
    // see dtos.py:ActionElement
    xpath: string
    html_element: any
    content: string
    details: any
    relevance: any // { string: float }
    id: number
    type: "LINK" | "BUTTON" | "INPUT"
    string: string
}

export type Action = {
    // see dtos.py:Action
    element?: ActionElement
    type: "CLICK" | "TYPE" | "TYPESUBMIT" | "NAVIGATE"
    value: string
}

export type ProcessRequestBody = {
    // see dtos.py:RequestBody
    data: WebpageData
    query: RelationQuery
    previous_actions: string[]
}

export type ProcessResponseBody = {
    // see dtos.py:ResponseBody
    results: Relation[]
    next_action?: Action
    confidence_level?: string
}