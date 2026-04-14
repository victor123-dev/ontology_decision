import { redirect } from "next/navigation";

export default function RootRedirectPage() {
  return redirect("/workspace");
}
