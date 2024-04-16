import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import type { Action } from "~types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getActionString(action: Action) {
  const actionValue = action.value ? " '" + action.value + "'" : ""
  const actionString = action.element.string ? " (" + action.element.string + ")" : ""
  return `${action.type}${actionValue}${actionString}`
}
