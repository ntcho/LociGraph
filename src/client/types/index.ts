export type Relation = {
    entity: string
    attribute: string
    value: string
}

export type RelationQuery = {
    entity: string
    attribute?: string
    value?: string
}

export type ActionElement = {
    xpath: string
    html_element: any
    content: string
    details: any
    relevance: any // { string: float }
    id: number
    type: "LINK" | "BUTTON" | "INPUT"
}

export type Action = {
    element: ActionElement
    type: "CLICK" | "TYPE" | "TYPESUBMIT"
    value: string
}