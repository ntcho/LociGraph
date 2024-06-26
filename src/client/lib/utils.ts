import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import type { Action, ActionElement, RelationQuery } from "~types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getActionString(action: Action) {
  const actionValue = action.value ? " '" + action.value + "'" : ""
  const actionString = action.element.string ?
    // remove element index from the string
    " (" + action.element.string.replace(/\[\d+\] */, "") + ")" : ""

  return `${action.type}${actionValue}${actionString}`
}

export function getActionDescription(action: Action) {
  const actionContent = action.element.type === "INPUT" ?
    getInputActionDetails(action.element) : action.element.content
  const actionValue = action.value ? " '" + action.value + "'" : ""

  if (actionContent === null) {
    return `${action.type} [${action.element.type}]${actionValue}`
  } else {
    return `${action.type} [${action.element.type} ${actionContent}]${actionValue}`
  }
}

export function getInputActionDetails(actionElement: ActionElement): string {
  // see dtos.py:ActionElement:getinputlabel() for server side implementation

  if (actionElement.type === "INPUT") {
    if (actionElement.details) {
      if (actionElement.details.hasOwnProperty("placeholder")) {
        return actionElement.details["placeholder"]
      } else if (actionElement.details.hasOwnProperty("aria-label")) {
        return actionElement.details["aria-label"]
      }
    }
  }

  return null
}

export function getExportFilename(query: RelationQuery) {
  const entity = query.entity
  const attribute = query.attribute ? `-${query.attribute}` : ""
  const value = query.value ? `-${query.value}` : ""

  const timestamp = new Date().toISOString().replace(/:/g, "-")

  return `locigraph_${timestamp}_${entity}${attribute}${value}`
}