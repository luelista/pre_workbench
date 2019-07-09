
export class LiteEvent<T>  {
    private handlers: { (data?: T): void; }[] = [];

    public on(handler: { (data?: T): void }) : void {
        this.handlers.push(handler);
    }

    public off(handler: { (data?: T): void }) : void {
        this.handlers = this.handlers.filter(h => h !== handler);
    }

    public trigger(data?: T) {
        this.handlers.slice(0).forEach(h => h(data));
    }
}

export function typedArrayToBuffer(array: Uint8Array): ArrayBuffer {
    return array.buffer.slice(array.byteOffset, array.byteLength + array.byteOffset)
}
export function bufferToHex (buffer : Uint8Array | ArrayBuffer) {
    return Array
        .from (new Uint8Array (buffer))
        .map (b => b.toString (16).padStart (2, "0"))
        .join ("");
}
export function EL(name:string, attrs:any, ...children:(string|HTMLElement)[]) : HTMLElement {
    var el = document.createElement(name);
    if (attrs) for(var key in attrs)
        if (key.startsWith("on")) el.addEventListener(key.substr(2), attrs[key], false);
        else el.setAttribute(key, attrs[key]);
    
    for(var i=0;i<children.length;i++){
        if (typeof children[i]=="string") el.appendChild(document.createTextNode(<string>children[i]));
        else el.appendChild(<HTMLElement>children[i]);
    }
    return el;
}