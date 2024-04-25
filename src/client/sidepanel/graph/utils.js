import { quadtree } from "d3-quadtree"
import { Position } from "reactflow"

// From https://reactflow.dev/examples/edges/floating-edges

// this helper function returns the intersection point
// of the line between the center of the intersectionNode and the target node
function getNodeIntersection(intersectionNode, targetNode) {
  // https://math.stackexchange.com/questions/1724792
  const {
    width: intersectionNodeWidth,
    height: intersectionNodeHeight,
    positionAbsolute: intersectionNodePosition
  } = intersectionNode
  const targetPosition = targetNode.positionAbsolute

  const w = intersectionNodeWidth / 2
  const h = intersectionNodeHeight / 2

  const x2 = intersectionNodePosition.x + w
  const y2 = intersectionNodePosition.y + h
  const x1 = targetPosition.x + targetNode.width / 2
  const y1 = targetPosition.y + targetNode.height / 2

  const xx1 = (x1 - x2) / (2 * w) - (y1 - y2) / (2 * h)
  const yy1 = (x1 - x2) / (2 * w) + (y1 - y2) / (2 * h)
  const a = 1 / (Math.abs(xx1) + Math.abs(yy1))
  const xx3 = a * xx1
  const yy3 = a * yy1
  const x = w * (xx3 + yy3) + x2
  const y = h * (-xx3 + yy3) + y2

  return { x, y }
}

// returns the edge position (top,right,bottom or right) from intersection point
function getEdgePosition(intersectionNode, targetNode, intersectionPoint) {
  const { x: tx, y: ty } = targetNode.positionAbsolute // left top corner of the node
  const { x: sx, y: sy } = intersectionNode.positionAbsolute // left top corner of the node

  const ix = intersectionPoint.x
  const iy = intersectionPoint.y

  const tn = targetNode

  // use intersection point first
  if (ix <= tx + 0.01) {
    return Position.Left
  }
  if (ix + 0.01 >= tx + tn.width) {
    return Position.Right
  }
  if (iy <= ty + 0.01) {
    return Position.Top
  }
  if (iy + 0.01 >= ty + tn.height) {
    return Position.Bottom
  }

  // use target node center as fallback
  if (sx <= tx + 0.01) {
    return Position.Left
  }
  if (sx + 0.01 >= tx + tn.width) {
    return Position.Right
  }
  if (sy <= ty + 0.01) {
    return Position.Top
  }
  if (sy + 0.01 >= ty + tn.height) {
    return Position.Bottom
  }

  return Position.Top
}

// returns the parameters (sx, sy, tx, ty, sourcePos, targetPos) you need to create an edge
export function getEdgeParams(source, target) {
  const sourceIntersectionPoint = getNodeIntersection(source, target)
  const targetIntersectionPoint = getNodeIntersection(target, source)

  const sourcePos = getEdgePosition(target, source, sourceIntersectionPoint)
  const targetPos = getEdgePosition(source, target, targetIntersectionPoint)

  return {
    sx: sourceIntersectionPoint.x,
    sy: sourceIntersectionPoint.y,
    tx: targetIntersectionPoint.x,
    ty: targetIntersectionPoint.y,
    sourcePos,
    targetPos
  }
}

// From https://reactflow.dev/learn/layouting/layouting#d3-force

export function collide() {
  let nodes = []
  let force = (alpha) => {
    const tree = quadtree(
      nodes,
      (d) => d.x,
      (d) => d.y
    )

    for (const node of nodes) {
      const r = node.width / 2
      const nx1 = node.x - r
      const nx2 = node.x + r
      const ny1 = node.y - r
      const ny2 = node.y + r

      tree.visit((quad, x1, y1, x2, y2) => {
        if (!quad.length) {
          do {
            if (quad.data !== node) {
              const r = node.width / 2 + quad.data.width / 2
              let x = node.x - quad.data.x
              let y = node.y - quad.data.y
              let l = Math.hypot(x, y)

              if (l < r) {
                l = ((l - r) / l) * alpha
                node.x -= x *= l
                node.y -= y *= l
                quad.data.x += x
                quad.data.y += y
              }
            }
          } while ((quad = quad.next))
        }

        return x1 > nx2 || x2 < nx1 || y1 > ny2 || y2 < ny1
      })
    }
  }

  force.initialize = (newNodes) => (nodes = newNodes)

  return force
}
