// Synthetic sample: tests actual exporter content binding, not production OCI.
package main
import("bytes";"fmt";"io";"os";"os/exec";"path/filepath";"github.com/google/go-containerregistry/pkg/v1/empty";"github.com/google/go-containerregistry/pkg/v1/layout";"github.com/google/go-containerregistry/pkg/v1/random";"github.com/google/go-containerregistry/pkg/v1/tarball")
func must(err error){if err!=nil{panic(err)}}
func main(){
 if len(os.Args)!=2{panic("exporter argument required")};exporter:=os.Args[1]
 root,err:=os.MkdirTemp("","order-b2-transport-");must(err);defer os.RemoveAll(root)
 img,err:=random.Image(2048,3);must(err);lp:=filepath.Join(root,"layout");l,err:=layout.Write(lp,empty.Index);must(err);must(l.AppendImage(img));d,err:=img.Digest();must(err)
 archive:=filepath.Join(root,"runtime.tar");cmd:=exec.Command(exporter,lp,d.String(),archive,"docker.io/local/order-b2-synthetic:checked");must(cmd.Run())
 got,err:=tarball.ImageFromPath(archive,nil);must(err);config,err:=img.RawConfigFile();must(err);other,err:=got.RawConfigFile();must(err);if !bytes.Equal(config,other){panic("config changed")}
 before,err:=img.Layers();must(err);after,err:=got.Layers();must(err);if len(before)!=len(after){panic("layer count")}
 for i,x:=range before{xd,err:=x.Digest();must(err);yd,err:=after[i].Digest();must(err);if xd!=yd{panic("compressed layer digest changed")};r,err:=x.Uncompressed();must(err);b,err:=io.ReadAll(r);must(err);must(r.Close());r,err=after[i].Uncompressed();must(err);a,err:=io.ReadAll(r);must(err);must(r.Close());if !bytes.Equal(a,b){panic("layer content changed")}}
 if exec.Command(exporter,lp,"sha256:0000000000000000000000000000000000000000000000000000000000000000",filepath.Join(root,"bad.tar"),"docker.io/local/order-b2-synthetic:checked").Run()==nil{panic("wrong digest accepted")}
 fmt.Println("PASS synthetic OCI transport: exact config bytes, three compressed layer digests and decompressed contents preserved; wrong digest refused. No production image assertion.")
}
